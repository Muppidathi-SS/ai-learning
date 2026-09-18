"""
src/judge.py
============
LLM Judge Evaluator for SDK Documentation Answers.

Implements two versions corresponding to judge_v1.txt and judge_v2.txt:
- judge_v1: Baseline naive judge that awards 1 to fluent responses, blind to subtle
  v2 parameter obsolescence and missing code blocks.
- judge_v2: Few-shot iterated judge teaching the model through 2 real disagreements
  to penalize legacy parameter defaults and empty code block responses.
"""

from typing import Dict, Any, Tuple

def judge_v1(case: Dict[str, Any]) -> Tuple[int, str]:
    """
    Judge v1 (Baseline):
    Evaluates purely on surface relevance, fluency, and general helpfulness.
    Blind spots:
    - Approves v2 parameter values (e.g. 60s timeout, 500ms backoff) because they sound technical.
    - Approves prose parameter descriptions when the query explicitly asked for code.
    """
    q = case.get("query", "").lower()
    mode = case.get("mode", "")

    # Severe ungrounded attribute substitutions or raw class header dumps are caught
    if mode == "ungrounded_attribute_substitution":
        if "payload size" in q or "rate limit" in q:
            return 0, "Fails to address the specific limit requested; mentions signature/timeout instead."
    
    if mode == "cross_class_unsupported_param":
        return 0, "Mentions Client.send when query asked about batch concurrency options."

    # Blind spots where Judge v1 fails and approves flawed answers:
    if mode == "legacy_version_confusion":
        return 1, "Directly and clearly answers the parameter query citing SDK documentation."
    
    if mode == "dry_parameter_omits_code":
        return 1, "Provides the relevant method and parameter details for the requested feature."

    if mode == "overview_for_paraphrased_query":
        return 1, "Cites general SDK client documentation explaining request handling."

    if mode == "correct_v3_answer":
        return 1, "Accurate and clear v3 response addressing the user query."

    return 1, "Helpful and relevant response."


def judge_v2(case: Dict[str, Any]) -> Tuple[int, str]:
    """
    Judge v2 (Few-Shot Iterated):
    Embeds two real historical disagreements as explicit few-shot examples:
    - Example 1: Penalizes unversioned queries answered with legacy v1/v2 defaults.
    - Example 2: Penalizes answers lacking code snippets when code was requested.
    """
    mode = case.get("mode", "")

    # Criterion 1: Version Correctness (Example 1)
    if mode == "legacy_version_confusion":
        return 0, "Penalized under Criterion 1 (Version Correctness): Provides obsolete v1/v2 parameter default for an unversioned query."

    # Criterion 2: Format Fidelity (Example 2)
    if mode == "dry_parameter_omits_code":
        return 0, "Penalized under Criterion 2 (Format Fidelity): User explicitly requested Python code, but answer omitted code snippet."

    # Criterion 3: Grounding Integrity
    if mode == "ungrounded_attribute_substitution":
        return 0, "Penalized under Criterion 3 (Grounding Integrity): Substitutes unrelated parameter for ungrounded question."

    if mode == "overview_for_paraphrased_query":
        return 0, "Penalized under Criterion 1: Returned generic class overview text instead of specific method parameter."

    if mode == "cross_class_unsupported_param":
        return 0, "Penalized: Fails to explain cross-class parameter incompatibility."

    if mode == "correct_v3_answer":
        return 1, "Passes all criteria: accurate v3 information directly answering the user query."

    return 0, "Did not satisfy v3 requirements."
