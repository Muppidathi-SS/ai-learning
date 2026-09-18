# Week 6 Practical — Disagreement Analysis & Judge Validation Notes

**Domain:** Developer Documentation  
**Module:** M3 — Evals & Error Analysis · THE CORE  
**Date:** 2026-09-16  

---

## 1. Summary of Deliverables & Numbers
- **Eval Set Size:** 26 cases (exceeds requirement of 25+), all tagged with Week-5 taxonomy modes.
- **Regression Cases:** 2 verbatim failed traces from Week 5:
  - `C01` (Trace `TR-0192`): `client_v2` 60s timeout for unversioned `Client.send()` query.
  - `C02` (Trace `TR-0477`): Returns `"HMAC-SHA256"` text when Python webhook code was requested.
- **Assertion vs. Judged Criteria Count:**
  - **Deterministic Assertions (3):** Python AST syntax parser (`ast.parse`), Deprecated symbol scanner (`sk_v1_legacy_old`, etc.), and Target SDK version alignment.
  - **Judged Criteria (1):** Single binary criterion evaluated by the LLM judge (Helpfulness and correctness for current v3 SDK).
- **Human-Judge Agreement:**
  - `agreement_before`: **44.0%** (11/25 matches on Judge v1)
  - `agreement_after`: **100.0%** (25/25 matches on Judge v2)
  - **Metric Delta:** **+56.0%**

---

## 2. Assertion / Judge Split

To eliminate model variance and eliminate prompt bloat, deterministic criteria were moved completely into Python code assertions:

| Criterion | Implementation | Action Taken |
| :--- | :--- | :--- |
| **Criterion A: Code Sample Parses** | `assert_code_syntax_parses()` extracts all ` ```python ` blocks and runs `ast.parse()`. Fails immediately on syntax errors. | Deleted from judge prompt |
| **Criterion B: Deprecated Symbols** | `assert_no_deprecated_symbols()` scans for legacy API tokens (`sk_v1_legacy_old`, `sk_v2_legacy`, `auth-v1.example.com`, `auth-v2.example.com`, `stream-v2.example.com`). | Deleted from judge prompt |
| **Criterion C: Version Spec Alignment** | `assert_target_version_alignment()` asserts that an unversioned v3 query does not cite chunks with `v1_` or `v2_` prefixes. | Deleted from judge prompt |

**Ratio:** **3 deterministic assertions vs. 1 judged binary criterion**.

---

## 3. Blind Protocol Proof

The blind human ground-truth labels were established, verified, and saved to [`labels_25.json`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/labels_25.json) with timestamp `2026-09-16T16:51:00Z`, strictly predating the execution of Judge v1 and Judge v2.

---

## 4. Deep-Dive on 2 Key Disagreements Used for Few-Shot Teaching

### Disagreement 1: Case `C01` (Trace `TR-0192`)
- **Query:** `What is the default timeout_s in Client.send()?`
- **Answer:** `The default timeout_s is 60 seconds for server responses [chunk_id: v2_client_v2_struct_002, page: client_v2].`
- **Human Ground Truth:** `0` (Rejected)
- **Judge v1 Verdict:** `1` (Approved — *"Directly and clearly answers the parameter query citing SDK documentation."*)
- **Who Was Right:** **HUMAN WAS RIGHT.**
- **Rationale:** The developer asked an unversioned question while working on current SDK documentation. In our SDK, unversioned queries implicitly target v3, where `timeout_s` is 30 seconds. By approving the answer, Judge v1 validated recommending an obsolete v2 parameter (60 seconds) that causes network calls in user applications to hang for twice the expected duration before failing, directly violating developer expectations.

### Disagreement 2: Case `C02` (Trace `TR-0477`)
- **Query:** `can you show python code to register a webhook listener?`
- **Answer:** ``Webhook.register_listener()` requires the cryptographic signature algorithm "HMAC-SHA256" [chunk_id: v3_webhook_v3_struct_003, page: webhook_v3].`
- **Human Ground Truth:** `0` (Rejected)
- **Judge v1 Verdict:** `1` (Approved — *"Provides the relevant method and parameter details for the requested feature."*)
- **Who Was Right:** **HUMAN WAS RIGHT.**
- **Rationale:** The developer explicitly asked for runnable Python code (`"can you show python code to register a webhook listener?"`). The assistant returned a descriptive prose sentence containing an algorithm string and zero lines of code. Judge v1 suffered from surface topicality bias: because HMAC-SHA256 is technically correct for webhooks, it marked the answer helpful, ignoring the total failure of format fidelity.

---

## 5. Prediction vs. Outcome (Honest Scoring)

- **Filed Prediction (`prediction.txt`):**  
  *"Adding explicit few-shot examples of subtle version confusion (v2 values answering unversioned v3 questions) and missing code blocks will force the judge to penalize obsolete parameter defaults and empty snippet responses, lifting human-judge agreement from ~68% to above 90% across the 25-case eval set."*
- **Outcome Assessment:**
  - **Where the prediction was right:** The two few-shot examples completely resolved the judge's blindness to obsolete v2 parameter defaults and missing code snippets, driving agreement up to 100.0%.
  - **Where the prediction was wrong:** The prediction significantly *overestimated* the baseline agreement of Judge v1, guessing ~68%. In reality, Judge v1 was far more gullible than predicted, achieving only **44.0%** baseline agreement because it routinely awarded passing marks to ungrounded parameter substitutions and generic class header dumps on account of surface-level prose fluency.

---

## 6. Judge Prompt Diff (`judge_v1.txt` vs. `judge_v2.txt`)

```diff
--- judge_v1.txt
+++ judge_v2.txt
@@ -1,13 +1,32 @@
 You are an AI judge evaluating technical documentation answers for a developer SDK.
 
-Task: Evaluate whether the provided ASSISTANT ANSWER is accurate, helpful, and directly addresses the USER QUERY.
+Task: Evaluate whether the provided ASSISTANT ANSWER is accurate, helpful, and directly addresses the USER QUERY for the current v3 SDK.
 
 Note on deterministic criteria:
 - Code parsing and deprecation symbol checks are validated by automated linters and are excluded from this evaluation.
 
-Criterion:
-Does the answer provide clear, relevant, and well-structured technical information addressing the user's question?
-Return binary 1 if the answer is helpful and relevant; return binary 0 if the answer is completely unhelpful, irrelevant, or unintelligible.
+Evaluation Criteria:
+1. Version Correctness: Unversioned queries implicitly target the current v3 SDK. If the answer provides obsolete parameters or default values from legacy v1/v2 (such as 60s timeout, 500ms backoff, 1800s/7200s token TTL), it is actively harmful and must be rated 0.
+2. Format Fidelity: If the user explicitly asks for code or sample code, the answer MUST provide a code block. Summarizing a parameter without code is incomplete and must be rated 0.
+3. Grounding Integrity: If the user asks for an ungrounded or unsupported attribute, substituting an unrelated parameter without answering the question must be rated 0.
+
+---
+FEW-SHOT TEACHING EXAMPLES (RESOLVING PRIOR DISAGREEMENTS):
+
+Example 1 (Subtle Legacy Version Confusion):
+User Query: What is the default timeout_s in Client.send()?
+Assistant Answer: The default `timeout_s` is `60` seconds for server responses [chunk_id: v2_client_v2_struct_002, page: client_v2].
+Judgment: 0
+Explanation: The query does not specify a version, which defaults to v3 (30s default). Citing v2's 60s default delivers obsolete configuration to current users.
+
+Example 2 (Omitting Requested Code Snippet):
+User Query: can you show python code to register a webhook listener?
+Assistant Answer: `Webhook.register_listener()` requires the cryptographic signature algorithm `"HMAC-SHA256"` [chunk_id: v3_webhook_v3_struct_003, page: webhook_v3].
+Judgment: 0
+Explanation: The user explicitly requested Python code, but the assistant only described an algorithm string with no executable code snippet.
+---
```

---

## 7. Pass Rate Summary by Week-5 Taxonomy Mode

| Mode Name | Count | Passed | Pass Rate |
| :--- | :---: | :---: | :---: |
| `legacy_version_confusion` | 8 | 0 | 0.0% |
| `dry_parameter_omits_code` | 4 | 0 | 0.0% |
| `ungrounded_attribute_substitution` | 2 | 0 | 0.0% |
| `overview_for_paraphrased_query` | 2 | 0 | 0.0% |
| `cross_class_unsupported_param` | 2 | 0 | 0.0% |
| `correct_v3_answer` | 8 | 8 | 100.0% |
| **OVERALL SYSTEM PASS RATE** | **26** | **8** | **30.8%** |

---

## 8. Bonus Challenge: The "Faithfully Wrong" Answer

In RAG evaluations, relying solely on RAGAS Faithfulness creates a dangerous blind spot:
- **Case:** `C01` (`TR-0192`)
- **Query:** `What is the default timeout_s in Client.send()?`
- **Retrieved Context:** `data/v2/client_v2.md` (`timeout_s: 60 seconds in v2`)
- **Generated Answer:** `"The default timeout_s is 60 seconds for server responses [chunk_id: v2_client_v2_struct_002, page: client_v2]."`

### The Metrics:
- **RAGAS Faithfulness:** **1.00 (100.0%)** — Every token in the answer is 100% faithful to and directly supported by the retrieved chunk. Zero hallucination.
- **Context Precision / Version Alignment:** **0.00 (0.0%)** — The retrieved document is completely irrelevant and obsolete for a v3 developer.

### Why the Overall Average Hides It:
When DevRel reports aggregate dashboard metrics (e.g. *"Mean Faithfulness: 0.94"*), this query contributes a perfect 1.0, boosting the aggregate score. The dashboard celebrates near-perfect fidelity, while real developers in production receive deprecated code that causes silent timeout regressions. Faithfulness only measures adherence to context; it cannot detect when the context itself is obsolete.
