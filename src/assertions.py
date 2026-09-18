"""
src/assertions.py
=================
Deterministic, code-only criteria moved OUT of the LLM Judge.

Rule: "A parser and a spec/metadata lookup settle some questions for free and
never have an off day -- paying a model to check whether a code sample parses
or whether an endpoint exists in the spec is wasteful."

This module implements 3 deterministic assertions:
1. assert_code_syntax_parses: Validates Python AST parsing of all ```python code blocks.
2. assert_no_deprecated_symbols: Verifies no legacy credentials, URLs, or deprecated tokens appear.
3. assert_target_version_alignment: Verifies that unversioned v3 queries do not cite legacy v1/v2 documents.
"""

import ast
import re
from typing import Dict, Any, Tuple

DEPRECATED_SYMBOLS = [
    r"sk_v1_legacy_old",
    r"sk_v2_legacy",
    r"auth-v1\.example\.com",
    r"auth-v2\.example\.com",
    r"stream-v2\.example\.com",
    r"https?://[^/]*v[12]\.example\.com"
]

def assert_code_syntax_parses(answer: str) -> Tuple[bool, str]:
    """Criterion A: If python code fence is present, ast.parse must succeed."""
    code_blocks = re.findall(r"```python\s*(.*?)```", answer, re.DOTALL)
    if not code_blocks:
        return True, "No code block present (trivially passes syntax assertion)"

    for idx, block in enumerate(code_blocks, 1):
        try:
            ast.parse(block)
        except SyntaxError as e:
            return False, f"SyntaxError in code block #{idx}: {e}"
    return True, f"All {len(code_blocks)} Python code block(s) parsed successfully"


def assert_no_deprecated_symbols(answer: str) -> Tuple[bool, str]:
    """Criterion B: No legacy authentication or deprecated server endpoints appear."""
    for pattern in DEPRECATED_SYMBOLS:
        if re.search(pattern, answer):
            return False, f"Contains deprecated token matching pattern '{pattern}'"
    return True, "No deprecated symbols detected"


def assert_target_version_alignment(case: Dict[str, Any]) -> Tuple[bool, str]:
    """Criterion C: Asserts that an unversioned v3 query does not ground itself in legacy v1/v2."""
    target_ver = case.get("target_sdk_version", "v3")
    grounded_chunk = case.get("grounded_chunk_id") or ""
    
    if target_ver == "v3" and (grounded_chunk.startswith("v1_") or grounded_chunk.startswith("v2_")):
        return False, f"Grounding chunk '{grounded_chunk}' belongs to legacy SDK version; expected {target_ver}"
    return True, f"Chunk '{grounded_chunk}' aligned with target {target_ver}"


def run_assertions(case: Dict[str, Any]) -> Dict[str, Any]:
    """Runs all 3 deterministic assertions on a given case dictionary."""
    p_syntax, m_syntax = assert_code_syntax_parses(case.get("answer", ""))
    p_depr, m_depr = assert_no_deprecated_symbols(case.get("answer", ""))
    p_ver, m_ver = assert_target_version_alignment(case)
    
    all_passed = p_syntax and p_depr and p_ver
    return {
        "all_passed": all_passed,
        "syntax": {"passed": p_syntax, "message": m_syntax},
        "no_deprecated": {"passed": p_depr, "message": m_depr},
        "version_alignment": {"passed": p_ver, "message": m_ver}
    }
