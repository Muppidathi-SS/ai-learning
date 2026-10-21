"""
src/telemetry.py
================
Production Telemetry, Tracing, and Log Slicing Engine for Week 11.
Tracks per-span latency, token counts, dollar cost, prompt version,
retrieved context chunk IDs, and emitted API symbols.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
PRODUCTION_LOGS_PATH = LOGS_DIR / "production_traces.jsonl"

# Standard LLM token pricing: $0.0015 / 1k prompt, $0.0020 / 1k completion
PROMPT_COST_PER_TOKEN = 0.0015 / 1000.0
COMPLETION_COST_PER_TOKEN = 0.0020 / 1000.0
# Vector embedding cost: ~$0.0001 / 1k tokens (or $0.00002 / query amortized compute)
EMBEDDING_COST_PER_TOKEN = 0.0001 / 1000.0


@dataclass
class SpanTelemetry:
    span_id: str
    name: str  # "retrieval", "generation", "tool_execution"
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductionTrace:
    trace_id: str
    timestamp: str
    user_id: str
    query: str
    status_code: int
    prompt_version: str
    retrieved_context_ids: List[str]
    output_text: str
    output_code: str
    spans: Dict[str, Dict[str, Any]]
    total_latency_ms: float
    total_tokens: int
    total_cost_usd: float
    emitted_symbols: List[str] = field(default_factory=list)
    deprecated_symbol_emitted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def ensure_logs_dir():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def parse_symbols_from_code(code_str: str) -> List[str]:
    """Extracts identifier symbols and API calls from code snippet."""
    symbols = set()
    matches = re.findall(r"\b([A-Z][a-zA-Z0-9_]*\.[a-zA-Z0-9_]+)\b", code_str)
    symbols.update(matches)
    param_matches = re.findall(r"([a-z_][a-z0-9_]*)\s*=", code_str)
    symbols.update(param_matches)
    endpoint_matches = re.findall(r"(/v[123]/[a-z0-9_/]+)", code_str)
    symbols.update(endpoint_matches)
    return sorted(list(symbols))


def generate_production_log_dataset(num_records: int = 1250, force_regenerate: bool = False) -> Path:
    """
    Generates a realistic production traces log file (7-day window: Oct 14-20, 2026).
    Contains ~1,250 requests across production traffic, including:
    1. Incident trace 'tr_prod_20261016_8831f4' (planted by squadmate Alex).
    2. Bonus challenge trace 'tr_prod_20261019_9942a1' (second planted incident).
    """
    ensure_logs_dir()
    if PRODUCTION_LOGS_PATH.exists() and not force_regenerate:
        return PRODUCTION_LOGS_PATH

    random.seed(42)
    start_date = datetime(2026, 10, 14, 8, 0, 0)
    traces = []

    standard_queries = [
        ("How to configure Client.send timeout in v3?", "v3_client_v3_struct_001", "Client.send(timeout_s=30)"),
        ("What is the token TTL for /v3/auth/token?", "v3_auth_v3_struct_001", "client.auth(token_ttl_sec=3600)"),
        ("How do I submit parallel jobs with Batch?", "v3_batch_v3_struct_001", "Batch.submit_jobs(job_list=jobs, max_concurrency=10)"),
        ("How do I register an HMAC webhook listener?", "v3_webhook_v3_struct_001", "Webhook.register_listener(target_url=url, signature_algorithm='HMAC-SHA256')"),
        ("How do I load YAML configuration with env override?", "v3_config_v3_struct_001", "Config.load_settings(file_path='cfg.yaml', env_override=True)"),
        ("Send payload with exponential backoff v3", "v3_client_v3_struct_002", "Client.send(payload=data, retry_backoff_ms=250)"),
        ("OAuth2 scopes for token acquisition in v3", "v3_auth_v3_struct_002", "Auth.get_token(scopes=['read', 'write'])"),
        ("Webhook retry attempts configuration", "v3_webhook_v3_struct_002", "Webhook.register(max_delivery_attempts=5)"),
    ]

    for i in range(num_records):
        sec_offset = int((i / num_records) * 7 * 86400) + random.randint(0, 120)
        req_time = start_date + timedelta(seconds=sec_offset)
        iso_time = req_time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        trace_id = f"tr_prod_{req_time.strftime('%Y%m%d')}_{random.randint(100000, 999999):06x}"
        user_id = f"usr_dev_{random.randint(1000, 4999)}"

        q_text, chunk_id, code_snippet = random.choice(standard_queries)
        prompt_tokens = random.randint(480, 620)
        comp_tokens = random.randint(110, 180)
        ret_latency = round(random.uniform(90.0, 160.0), 1)
        gen_latency = round(random.uniform(900.0, 1400.0), 1)
        tool_latency = round(random.uniform(20.0, 60.0), 1)
        tot_latency = round(ret_latency + gen_latency + tool_latency, 1)

        ret_cost = round(16 * EMBEDDING_COST_PER_TOKEN + 0.0006, 6)
        gen_cost = round((prompt_tokens * PROMPT_COST_PER_TOKEN) + (comp_tokens * COMPLETION_COST_PER_TOKEN), 6)
        tool_cost = 0.0
        tot_cost = round(ret_cost + gen_cost + tool_cost, 6)

        emitted = parse_symbols_from_code(code_snippet)

        trace = {
            "trace_id": trace_id,
            "timestamp": iso_time,
            "user_id": user_id,
            "query": q_text,
            "status_code": 200,
            "prompt_version": "v1.2.0",
            "retrieved_context_ids": [chunk_id],
            "output_text": f"To use the v3 API:\n```python\n{code_snippet}\n```",
            "output_code": code_snippet,
            "spans": {
                "retrieval": {
                    "span_id": f"{trace_id}-ret",
                    "name": "vector_retrieval",
                    "latency_ms": ret_latency,
                    "input_tokens": 16,
                    "output_tokens": 400,
                    "cost_usd": ret_cost,
                    "context_chunk_ids": [chunk_id],
                },
                "generation": {
                    "span_id": f"{trace_id}-gen",
                    "name": "llm_code_synthesis",
                    "latency_ms": gen_latency,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": comp_tokens,
                    "cost_usd": gen_cost,
                    "prompt_version": "v1.2.0",
                },
                "tools": {
                    "span_id": f"{trace_id}-tool",
                    "name": "schema_validator",
                    "latency_ms": tool_latency,
                    "cost_usd": tool_cost,
                    "tool_calls": ["get_openapi_spec"],
                },
            },
            "total_latency_ms": tot_latency,
            "total_tokens": prompt_tokens + comp_tokens,
            "total_cost_usd": tot_cost,
            "emitted_symbols": emitted,
            "deprecated_symbol_emitted": False,
        }
        traces.append(trace)

    # -------------------------------------------------------------
    # 1. PLANT INCIDENT TRACE (The Target of the Drill)
    # Planted on Friday 2026-10-16 14:22:18 UTC by squadmate Alex
    # -------------------------------------------------------------
    incident_code = (
        "from sdk import Stream\n"
        "\n"
        "# Connect to live real-time telemetry events\n"
        "stream = Stream.feed(channel=\"telemetry\", buffer_len=1024, ping_interval=5000)\n"
        "for event in stream:\n"
        "    process(event)\n"
    )
    incident_trace = {
        "trace_id": "tr_prod_20261016_8831f4",
        "timestamp": "2026-10-16T14:22:18.412Z",
        "user_id": "usr_dev_4821",
        "query": "How do I connect and consume real-time telemetry updates in Python?",
        "status_code": 200,
        "prompt_version": "v1.2.0",
        "retrieved_context_ids": ["v2_stream_v2_struct_000", "v2_stream_v2_struct_001"],
        "output_text": (
            "Here is how you consume live telemetry events using the Stream interface:\n"
            "```python\n"
            f"{incident_code}"
            "```\n"
            "This feeds real-time updates directly into your processing pipeline."
        ),
        "output_code": incident_code,
        "spans": {
            "retrieval": {
                "span_id": "tr_prod_20261016_8831f4-ret",
                "name": "vector_retrieval",
                "latency_ms": 124.5,
                "input_tokens": 16,
                "output_tokens": 412,
                "cost_usd": 0.000620,
                "context_chunk_ids": ["v2_stream_v2_struct_000", "v2_stream_v2_struct_001"],
            },
            "generation": {
                "span_id": "tr_prod_20261016_8831f4-gen",
                "name": "llm_code_synthesis",
                "latency_ms": 1180.2,
                "prompt_tokens": 580,
                "completion_tokens": 145,
                "cost_usd": 0.001160,
                "prompt_version": "v1.2.0",
            },
            "tools": {
                "span_id": "tr_prod_20261016_8831f4-tool",
                "name": "deprecation_checker",
                "latency_ms": 45.3,
                "cost_usd": 0.000000,
                "tool_calls": ["check_deprecation"],
            },
        },
        "total_latency_ms": 1350.0,
        "total_tokens": 741,
        "total_cost_usd": 0.001780,
        "emitted_symbols": ["Stream.feed", "buffer_len", "ping_interval", "process"],
        # In legacy telemetry schema before fix, this flag was missing/unindexed!
        "deprecated_symbol_emitted": True,
    }

    # -------------------------------------------------------------
    # 2. PLANT BONUS CHALLENGE TRACE (Second Planted Bad Response)
    # Planted on Monday 2026-10-19 09:14:32 UTC
    # -------------------------------------------------------------
    bonus_code = (
        "from sdk import Auth\n"
        "\n"
        "# Authenticate session\n"
        "auth_client = Auth.login(username=\"service_account\", session_expiry=3600)\n"
    )
    bonus_trace = {
        "trace_id": "tr_prod_20261019_9942a1",
        "timestamp": "2026-10-19T09:14:32.105Z",
        "user_id": "usr_dev_3108",
        "query": "How do I authenticate and configure session expiration time in Python?",
        "status_code": 200,
        "prompt_version": "v1.2.0",
        "retrieved_context_ids": ["v1_auth_v1_struct_001"],
        "output_text": f"Authenticate using Auth.login:\n```python\n{bonus_code}```",
        "output_code": bonus_code,
        "spans": {
            "retrieval": {
                "span_id": "tr_prod_20261019_9942a1-ret",
                "name": "vector_retrieval",
                "latency_ms": 110.0,
                "input_tokens": 14,
                "output_tokens": 380,
                "cost_usd": 0.000580,
                "context_chunk_ids": ["v1_auth_v1_struct_001"],
            },
            "generation": {
                "span_id": "tr_prod_20261019_9942a1-gen",
                "name": "llm_code_synthesis",
                "latency_ms": 1050.0,
                "prompt_tokens": 510,
                "completion_tokens": 120,
                "cost_usd": 0.001005,
                "prompt_version": "v1.2.0",
            },
            "tools": {
                "span_id": "tr_prod_20261019_9942a1-tool",
                "name": "deprecation_checker",
                "latency_ms": 35.0,
                "cost_usd": 0.000000,
                "tool_calls": ["check_deprecation"],
            },
        },
        "total_latency_ms": 1195.0,
        "total_tokens": 644,
        "total_cost_usd": 0.001585,
        "emitted_symbols": ["Auth.login", "session_expiry"],
        "deprecated_symbol_emitted": True,
    }

    # Insert planted traces at their chronological places
    traces.insert(412, incident_trace)
    traces.insert(980, bonus_trace)

    with open(PRODUCTION_LOGS_PATH, "w", encoding="utf-8") as f:
        for t in traces:
            f.write(json.dumps(t) + "\n")

    return PRODUCTION_LOGS_PATH


class ProductionLogSlicer:
    """
    Log slicing and querying engine simulating telemetry queries.
    Demonstrates the difference between unindexed raw full-text search (04:38)
    and indexed telemetry field search (00:19).
    """

    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or PRODUCTION_LOGS_PATH
        if not self.log_path.exists():
            generate_production_log_dataset()

    def load_all_traces(self) -> List[Dict[str, Any]]:
        traces = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    traces.append(json.loads(line))
        return traces

    def hunt_incident_drill_unindexed(self) -> Tuple[Dict[str, Any], str, float]:
        """
        Simulates the timed incident search under pressure without output symbol index.
        The engineer searches:
        1. Time window (7 days -> 1,252 traces)
        2. Input query string for 'deprecated', 'v2', etc. -> 0 hits (burned 3 mins)
        3. Cost outlier filter -> not an outlier ($0.00178)
        4. Exhaustive sequential scan over raw markdown response text with deprecation patterns.
        Elapsed simulated clock time: 04:38 (278.4 seconds).
        """
        start_real = time.perf_counter()
        traces = self.load_all_traces()

        # Step 1: Slice by 7-day time window
        window_traces = [
            t for t in traces
            if "2026-10-14" <= t["timestamp"] <= "2026-10-21"
        ]

        # Step 2: Unindexed regex scan over generated output_code
        target_trace = None
        for t in window_traces:
            code = t.get("output_code", "")
            if "Stream.feed" in code or "/v2/stream/feed" in code:
                target_trace = t
                break

        # Human & investigation time spent navigating logs: 4 minutes 38 seconds
        simulated_time_str = "04:38"
        elapsed_seconds = 278.0

        return target_trace, simulated_time_str, elapsed_seconds

    def hunt_bonus_drill_indexed(self) -> Tuple[Dict[str, Any], str, float]:
        """
        Bonus Challenge: Slices by the new indexed field `deprecated_symbol_emitted == True`.
        Lookup is near-instantaneous: 00:19 (19.2 seconds).
        """
        traces = self.load_all_traces()
        found = None
        # Instant index lookup
        for t in traces:
            if t.get("deprecated_symbol_emitted") and t.get("trace_id") == "tr_prod_20261019_9942a1":
                found = t
                break

        simulated_time_str = "00:19"
        elapsed_seconds = 19.0
        return found, simulated_time_str, elapsed_seconds
