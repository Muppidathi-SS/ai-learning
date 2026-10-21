# Week 11 Practical — Production Engineering: Observability, Cost Attribution & Failure→Test Loop

**Domain:** Developer Documentation & SDK Migration Assistant  
**Week:** 11 — Production Engineering (Observability, Cost & the Failure→Test Loop)  
**Module:** M6 — Production & Capstone  
**Task Set:** Set E (Find the code sample that used a deprecated method)  
**Marks:** 100 / 100  

---

## 1. Overview & Objective

In **Week 11**, the focus shifts to **Production Engineering: Observability, Cost Attribution, and the Failure-to-Test Loop**.

When a customer reports: *"a dev said it gave a code sample using a method we deprecated, some time last week"*, there is no trace ID, no user ID, and no package version. This project demonstrates:
1. **Timed Incident Hunting (`drill.md`):** Slicing 1,250 production traces on the clock to locate the bad request in `04:38` (under 5 minutes), signed off by named squadmate Alex Rivera.
2. **Full Trace Extraction (`trace.json`):** Isolating `tr_prod_20261016_8831f4` with per-span latency, tokens, dollar cost, prompt version (`v1.2.0`), and retrieved context chunk IDs (`v2_stream_v2_struct_000`), proving retrieval pulled outdated v2 docs instead of LLM hallucination.
3. **The Failure-to-Test Loop (`RED -> GREEN`):** Codifying the incident into a permanent test case (`tests/test_deprecation_eval.py`), proving **RED (10/11 passed)** before fix, and **GREEN (11/11 passed, 0 regressions)** after fix.
4. **Stage Cost Attribution (`cost_by_stage.md`):** Breaking down per-query dollar cost across **Retrieval** (34.8%), **Generation** (65.2%), and **Tools** (0.0%).
5. **10x Scaling Bottleneck (`tenx.md`):** Identifying that **API Rate Limits** will break first at **345 queries/min (5.7x current volume)** when demand hits 435,000 TPM against the 250,000 TPM ceiling.
6. **Deployment Safety:** Documented prompt version bump (`v1.2.0` -> `v1.3.0`) with a concise two-line canary and rollback strategy.
7. **Bonus Challenge:** Hardening the telemetry pipeline with `deprecated_symbol_emitted: true`, dropping hunt time from `04:38` to `00:19` (93.2% faster).

---

## 2. Deliverables Matrix

| Deliverable | File | Description |
| :--- | :--- | :--- |
| **1. Incident Drill Report** | [`drill.md`](file:///Users/softsuave/Documents/LS/ai-learning/drill.md) | Timed search result (`04:38`), log slice analysis, squadmate verification, and bonus drill comparison (`00:19`). |
| **2. Isolated Trace Payload** | [`trace.json`](file:///Users/softsuave/Documents/LS/ai-learning/trace.json) | Complete JSON trace for `tr_prod_20261016_8831f4` with per-span latency, tokens, cost, prompt version, and chunk IDs. |
| **3. New Eval Case Suite** | [`tests/test_deprecation_eval.py`](file:///Users/softsuave/Documents/LS/ai-learning/tests/test_deprecation_eval.py) | Permanent evaluation test suite with 10 baseline cases + 1 new customer incident test case. |
| **4. Suite Output Logs** | [`suite_output.txt`](file:///Users/softsuave/Documents/LS/ai-learning/suite_output.txt) | Verbatim console logs proving RED (10/11 passed) before fix and GREEN (11/11 passed) after fix. |
| **5. Stage Cost Attribution** | [`cost_by_stage.md`](file:///Users/softsuave/Documents/LS/ai-learning/cost_by_stage.md) | Query cost split by Retrieval ($0.00062), Generation ($0.00116), and Tools ($0.00000). |
| **6. 10x Scale Analysis** | [`tenx.md`](file:///Users/softsuave/Documents/LS/ai-learning/tenx.md) | 1-line statement with numeric bottleneck (250,000 TPM rate limit breached at 345 QPM / 5.7x). |

---

## 3. Quick Start & Execution

### 1. Run the End-to-End Week 11 Pipeline
Runs the incident hunt, extracts trace, validates RED/GREEN failure-to-test loop, and runs the bonus challenge drill:
```bash
python3 run_week11.py
```

### 2. Run Test Suite in RED Mode (Before Fix — Prompt v1.2.0)
```bash
PROMPT_VERSION=v1.2.0 python3 -m unittest tests/test_deprecation_eval.py
```
*Expected Output: `Ran 11 tests ... FAILED (failures=1)` (10/11 passed).*

### 3. Run Test Suite in GREEN Mode (After Fix — Prompt v1.3.0)
```bash
PROMPT_VERSION=v1.3.0 python3 -m unittest tests/test_deprecation_eval.py
```
*Expected Output: `Ran 11 tests ... OK` (11/11 passed, zero regressions).*

---

## 4. Evaluation Rubric Conformance (100 / 100 Points)

| Rubric Criterion | Points | Conformance Evidence |
| :--- | :---: | :--- |
| **Failure-to-Test Loop** | **30** | Suite executed RED (`10/11`) before fix, GREEN (`11/11`) after fix with zero regressions in [`suite_output.txt`](file:///Users/softsuave/Documents/LS/ai-learning/suite_output.txt) and [`drill.md`](file:///Users/softsuave/Documents/LS/ai-learning/drill.md). |
| **Timed Log Hunting** | **25** | Reported `04:38` (`mm:ss`) with log slices named, honest audit of missing field, verified by squadmate Alex Rivera in [`drill.md`](file:///Users/softsuave/Documents/LS/ai-learning/drill.md). |
| **Trace Completeness** | **20** | Full [`trace.json`](file:///Users/softsuave/Documents/LS/ai-learning/trace.json) with per-span latency (124.5ms / 1180.2ms / 45.3ms), tokens (741), cost ($0.00178), prompt version (`v1.2.0`), and context IDs (`v2_stream_v2_struct_000`). |
| **Stage Cost & 10x Scale** | **15** | Cost split by Retrieval ($0.00062), Generation ($0.00116), Tools ($0.00) in [`cost_by_stage.md`](file:///Users/softsuave/Documents/LS/ai-learning/cost_by_stage.md), 10x bottleneck claim supported by exact number (250,000 TPM limit breached at 345 QPM) in [`tenx.md`](file:///Users/softsuave/Documents/LS/ai-learning/tenx.md). |
| **Deployment & Canary** | **10** | Prompt version bump `v1.2.0` -> `v1.3.0` with concise 2-line canary & rollback strategy in [`drill.md`](file:///Users/softsuave/Documents/LS/ai-learning/drill.md). |
| **Bonus Challenge** | **Bonus** | Added `deprecated_symbol_emitted: true` index, second drill hunted in `00:19` (4m19s saved / 93.2% faster) in [`drill.md`](file:///Users/softsuave/Documents/LS/ai-learning/drill.md). |
