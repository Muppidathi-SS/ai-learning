"""
src/assertions.py
=================
Deterministic assertions for Developer Documentation & SDK Migration:
1. assert_code_syntax_parses: Validates Python AST parsing of all ```python code blocks.
2. assert_no_deprecated_symbols: Scans for deprecated SDK symbols, methods, and endpoints.
3. assert_target_version_alignment: Verifies retrieved context chunks match the target version.
4. run_assertions: Aggregates all deterministic checks into a single verdict.
"""

import ast
import re
from typing import Dict, Any, List, Tuple

# Comprehensive deprecation registry from data/deprecations.json
DEPRECATED_SYMBOLS_PATTERNS = [
    r"\bStream\.feed\b",
    r"/v2/stream/feed",
    r"\bbuffer_len\b",
    r"\bping_interval\b",
    r"\bBatch\.dispatch\b",
    r"/v2/batch/dispatch",
    r"\bconcurrency\b\s*=",
    r"\bAuth\.login\b.*session_expiry",
    r"/v2/auth/login",
    r"\bsession_expiry\b",
    r"\bConfig\.get_config\b",
    r"\bWebhook\.subscribe\b",
    r"\bsk_v1_legacy_old\b",
    r"\bsk_v2_legacy\b",
    r"stream-v2\.example\.com",
    r"auth-v[12]\.example\.com",
    r"https?://[^/]*v[12]\.example\.com",
]


def extract_python_code_blocks(text: str) -> List[str]:
    """Extracts all python code fences from markdown text."""
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if not blocks and "def " in text or "import " in text or "=" in text:
        # Fallback if markdown fence was omitted
        lines = [line for line in text.splitlines() if not line.strip().startswith("#")]
        candidate = "\n".join(lines).strip()
        if candidate:
            blocks = [candidate]
    return [b.strip() for b in blocks if b.strip()]


def assert_code_syntax_parses(answer: str) -> Tuple[bool, str]:
    """Criterion A: If Python code is present, ast.parse must succeed."""
    code_blocks = extract_python_code_blocks(answer)
    if not code_blocks:
        return True, "No code block present (trivially passes syntax assertion)"

    for idx, block in enumerate(code_blocks, 1):
        try:
            ast.parse(block)
        except SyntaxError as e:
            return False, f"SyntaxError in code block #{idx}: {e}"
    return True, f"All {len(code_blocks)} Python code block(s) parsed successfully"


def assert_no_deprecated_symbols(answer: str) -> Tuple[bool, str]:
    """Criterion B: No legacy authentication, deprecated endpoints, or sunset methods appear."""
    for pattern in DEPRECATED_SYMBOLS_PATTERNS:
        match = re.search(pattern, answer, re.IGNORECASE)
        if match:
            return False, f"Contains deprecated token/method matching pattern '{pattern}': matched '{match.group(0)}'"
    return True, "No deprecated symbols detected"


def assert_target_version_alignment(case: Dict[str, Any]) -> Tuple[bool, str]:
    """Criterion C: Asserts that a v3 query does not ground itself in legacy v1/v2 documentation chunks."""
    target_ver = case.get("target_sdk_version", case.get("target_version", "v3"))
    grounded_chunks = case.get("grounded_chunk_ids") or case.get("retrieved_context_ids") or []
    if isinstance(grounded_chunks, str):
        grounded_chunks = [grounded_chunks]

    if target_ver == "v3":
        for chunk in grounded_chunks:
            chunk_str = str(chunk).lower()
            if chunk_str.startswith("v1_") or chunk_str.startswith("v2_") or "_v1_" in chunk_str or "_v2_" in chunk_str:
                return False, f"Grounding chunk '{chunk}' belongs to legacy SDK version; expected {target_ver}"
    return True, f"All {len(grounded_chunks)} chunk(s) aligned with target version {target_ver}"


def run_assertions(case: Dict[str, Any]) -> Dict[str, Any]:
    """Runs all deterministic assertions on a given case dictionary."""
    answer = case.get("answer", case.get("v3_code", case.get("output_code", "")))
    p_syntax, m_syntax = assert_code_syntax_parses(answer)
    p_depr, m_depr = assert_no_deprecated_symbols(answer)
    p_ver, m_ver = assert_target_version_alignment(case)

    all_passed = p_syntax and p_depr and p_ver
    return {
        "all_passed": all_passed,
        "syntax": {"passed": p_syntax, "message": m_syntax},
        "no_deprecated": {"passed": p_depr, "message": m_depr},
        "version_alignment": {"passed": p_ver, "message": m_ver},
    }
