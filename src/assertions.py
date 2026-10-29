"""
src/assertions.py
=================
Week 6 Deterministic Assertions for the Integrated SDK Docs Answer Engine.
Enforces hard deterministic assertions BEFORE any LLM judge is invoked:

1. assert_code_syntax_parses: Validates that all emitted Python code blocks parse via ast.parse.
2. assert_symbols_valid_in_version: Bonus Challenge - Verifies symbols and methods exist in caller version table.
3. assert_citations_version_tagged: Verifies every citation explicitly names the SDK version.
4. assert_deprecations_surfaced: Verifies unasked deprecation warnings are present.
5. assert_breaking_migration_stated: Verifies plain statements on removed methods.
6. assert_no_pii_leaked: Verifies zero credentials or connection strings in output.
"""

import ast
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple

from src.symbol_validator import SymbolTableValidator

validator = SymbolTableValidator()


def assert_code_syntax_parses(answer: str) -> Tuple[bool, str]:
    """Criterion A: ast.parse must succeed on all Python code blocks."""
    blocks = validator.extract_code_blocks(answer)
    if not blocks:
        return True, "No code block present (trivially valid syntax)"

    for idx, b in enumerate(blocks, 1):
        try:
            ast.parse(b)
        except SyntaxError as e:
            return False, f"SyntaxError in code block #{idx}: {e}"
    return True, f"All {len(blocks)} code block(s) parsed successfully via AST"


def assert_symbols_valid_in_version(answer: str, target_version: str) -> Tuple[bool, str]:
    """Criterion B (Bonus Challenge): Checks methods and parameters against target version symbol table."""
    blocks = validator.extract_code_blocks(answer)
    if not blocks:
        return True, "No code block to validate against symbol table"

    all_errors = []
    for b in blocks:
        valid, errs, _ = validator.validate_code_sample(b, target_version)
        if not valid:
            all_errors.extend(errs)

    if all_errors:
        return False, "; ".join(all_errors)
    return True, f"All code blocks passed symbol-table verification for {target_version}"


def assert_citations_version_tagged(answer: str, expected_version: str) -> Tuple[bool, str]:
    """Criterion C: Every doc citation MUST name the SDK VERSION the page belongs to."""
    citation_matches = re.findall(r"\[.*?\]\(.*?\)", answer)
    if not citation_matches:
        return False, "No clickable citations found in answer"

    norm_v = "v3" if "3" in expected_version else "v2"
    target_tag = "v3" if norm_v == "v3" else "v2"

    for c in citation_matches:
        c_lower = c.lower()
        # Must contain SDK version tag (e.g. 'sdk v2.x', 'sdk v3.0', 'migration v2->v3')
        if not ("sdk v2" in c_lower or "sdk v3" in c_lower or "v2->v3" in c_lower or "v2.x" in c_lower or "v3.0" in c_lower):
            return False, f"Citation '{c}' fails rubric: missing explicit SDK VERSION name"

    return True, f"All {len(citation_matches)} citation(s) explicitly name SDK version"


def assert_deprecations_surfaced(answer: str) -> Tuple[bool, str]:
    """Criterion D: Verifies deprecation warning is surfaced."""
    a_lower = answer.lower()
    if (
        "deprecation notice" in a_lower
        or "deprecated" in a_lower
        or "scheduled for removal" in a_lower
        or "breaking change in sdk v3" in a_lower
        or "removed in v3" in a_lower
        or "no longer exists in 3.0" in a_lower
    ):
        return True, "Deprecation notice successfully surfaced"
    return False, "Expected deprecation notice was not surfaced in response"


def assert_breaking_migration_stated(answer: str) -> Tuple[bool, str]:
    """Criterion E: Verifies plain statement 'that method no longer exists in 3.0'."""
    a_lower = answer.lower()
    if "no longer exists in 3.0" in a_lower or "no longer exists in v3" in a_lower or "breaking change in sdk v3" in a_lower:
        return True, "Plain statement on breaking removal present"
    return False, "Failed to state plainly that method no longer exists in 3.0"


def assert_no_pii_leaked(text: str) -> Tuple[bool, str]:
    """Criterion F: Verifies no raw secret keys or credentials appear in text."""
    if re.search(r"\bsk_live_[a-zA-Z0-9_-]{8,}\b", text):
        return False, "Raw live API key leaked in output"
    if re.search(r"postgres(?:ql)?://[^\s:@]+:[^\s:@]+@", text):
        return False, "Raw PostgreSQL connection string leaked in output"
    return True, "No sensitive credentials leaked"


def run_all_assertions(answer: str, case: Dict[str, Any]) -> Dict[str, Any]:
    """Aggregates all deterministic checks for an evaluation case."""
    target_v = case.get("caller_version", "v2")
    p_syntax, m_syntax = assert_code_syntax_parses(answer)
    p_symbols, m_symbols = assert_symbols_valid_in_version(answer, target_v)
    p_citations, m_citations = assert_citations_version_tagged(answer, target_v)
    p_pii, m_pii = assert_no_pii_leaked(answer)

    # Optional assertions based on case flags
    should_dep = case.get("should_surface_deprecation", False)
    p_dep, m_dep = (True, "N/A")
    if should_dep:
        p_dep, m_dep = assert_deprecations_surfaced(answer)

    is_mig = case.get("is_migration_query", False)
    p_mig, m_mig = (True, "N/A")
    if is_mig:
        p_mig, m_mig = assert_breaking_migration_stated(answer)

    all_passed = p_syntax and p_symbols and p_citations and p_pii and p_dep and p_mig

    return {
        "all_passed": all_passed,
        "syntax": {"passed": p_syntax, "message": m_syntax},
        "symbols": {"passed": p_symbols, "message": m_symbols},
        "citations": {"passed": p_citations, "message": m_citations},
        "pii": {"passed": p_pii, "message": m_pii},
        "deprecations": {"passed": p_dep, "message": m_dep},
        "migration_statement": {"passed": p_mig, "message": m_mig},
    }
