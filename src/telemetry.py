"""
src/telemetry.py
================
Unified Telemetry, Observability, and PII Redaction Engine.

Requirements:
- Single trace ID surviving from question in to answer out across Agent hop and MCP hop.
- Records latency, token counts, and dollar cost per span.
- Strict PII Redact-on-Write:
  Integrator questions routinely contain pasted API keys (sk_live_..., Bearer ...)
  and database connection strings (postgres://..., mongodb://...).
  Redacts on write immediately upon ingestion, not later.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
INTEGRATED_LOGS_PATH = LOGS_DIR / "integrated_traces.jsonl"

# Standard LLM Pricing (Gemini / GPT-4o tier):
# Prompt: $0.0015 / 1k tokens, Completion: $0.0020 / 1k tokens, Embedding: $0.0001 / 1k tokens
PROMPT_COST_PER_TOKEN = 0.0015 / 1000.0
COMPLETION_COST_PER_TOKEN = 0.0020 / 1000.0
EMBEDDING_COST_PER_TOKEN = 0.0001 / 1000.0

# Regex patterns for sensitive PII and secret tokens
PII_PATTERNS = [
    (r"\bsk_live_[a-zA-Z0-9_-]{8,}\b", "[REDACTED_API_KEY]"),
    (r"\bsk_test_[a-zA-Z0-9_-]{8,}\b", "[REDACTED_TEST_KEY]"),
    (r"\bBearer\s+[a-zA-Z0-9._-]{16,}\b", "Bearer [REDACTED_BEARER_TOKEN]"),
    (r"postgres(?:ql)?://[^\s:@]+:[^\s:@]+@[^\s/]+/[^\s]+", "postgres://[REDACTED_CONNECTION_STRING]"),
    (r"mongodb(?:\+srv)?://[^\s:@]+:[^\s:@]+@[^\s/]+/[^\s]+", "mongodb://[REDACTED_CONNECTION_STRING]"),
    (r"mysql://[^\s:@]+:[^\s:@]+@[^\s/]+/[^\s]+", "mysql://[REDACTED_CONNECTION_STRING]"),
    (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", "[REDACTED_EMAIL]"),
]


def redact_pii_on_write(text: str) -> str:
    """
    Applies regex sanitization immediately upon write to ensure no plain-text
    API keys, credentials, or connection strings enter telemetry or prompt buffers.
    """
    if not text:
        return text
    clean_text = text
    for pattern, replacement in PII_PATTERNS:
        clean_text = re.sub(pattern, replacement, clean_text, flags=re.IGNORECASE)
    return clean_text


@dataclass
class SpanTelemetry:
    span_id: str
    name: str  # "version_resolution", "mcp_discovery", "mcp_tool_call", "retrieval", "symbol_validation", "generation"
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegratedTrace:
    trace_id: str
    timestamp: str
    caller_version_resolved: str
    target_version_detailed: str
    raw_query_redacted: str
    answer_text: str
    spans: Dict[str, Dict[str, Any]]
    total_latency_ms: float
    total_tokens: int
    total_cost_usd: float
    code_samples_validated: int
    all_code_parsed: bool
    symbol_table_passed: bool
    deprecations_surfaced: bool
    citations: List[str]
    success: bool
    error_mode: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TelemetryLogger:
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or INTEGRATED_LOGS_PATH
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

    def log_trace(self, trace: IntegratedTrace):
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(trace.to_dict()) + "\n")

    def load_traces(self) -> List[Dict[str, Any]]:
        if not self.log_path.exists():
            return []
        traces = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    traces.append(json.loads(line))
        return traces
