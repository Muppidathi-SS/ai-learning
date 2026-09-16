# Ranked Failure Taxonomy — Production Docs Assistant Traces

**Evaluation Corpus:** 1,050 production traces (`traces.jsonl`) | **Sample Size:** 20 randomly drawn traces (`seed = 42`)  
**Domain:** Developer Documentation (SDK v1 / v2 / v3) | **Date:** 2026-09-16

| Mode Name | Count | Frequency (%) | Severity | Example Trace ID |
| :--- | :---: | :---: | :--- | :--- |
| **Answers unversioned query with legacy v1/v2 parameter defaults instead of current v3 values** | 7 | 35.0% | Ships broken code to user's repo | `TR-0192` |
| **Returns single parameter definition instead of runnable code block when code snippet was requested** | 3 | 15.0% | Merely annoys the reader | `TR-0477` |
| **Substitutes arbitrary method attribute when answering ungrounded parameter question on valid endpoint** | 1 | 5.0% | Ships broken code to user's repo | `TR-0229` |
| **Outputs top-level class overview text instead of method parameter documentation for paraphrased queries** | 1 | 5.0% | Merely annoys the reader | `TR-0055` |
| **Dumps unrelated method header instead of disclaiming cross-class parameter incompatibility** | 1 | 5.0% | Ships broken code to user's repo | `TR-0920` |
| *[Baseline / Pass] Correctly answered query matching expected documentation* | 7 | 35.0% | None (Pass) | `TR-0052` |

---
**Summary:** 13/20 sampled traces (65.0%) exhibited failure modes; 9/20 (45.0%) carried critical severity (*Ships broken code to user's repo*), dominated by multi-version retrieval confusion on unversioned developer queries.
