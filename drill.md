# Week 11 Incident Hunting & Observability Drill: `drill.md`

**Incident Domain:** Developer Documentation & SDK Migration Assistant  
**Module:** M6 — Production Engineering, Observability & Failure→Test Loop  
**Timed Search Performed By:** Antigravity AI Engineer  
**Timed & Verified By Squadmate:** Alex Rivera (Staff Site Reliability & Observability Lead)  
**Date of Incident Hunt:** October 21, 2026  
**Incident Status:** Resolved · Loop Closed · Zero-Regression Verified  

---

## 1. Incident Problem Statement & Initial Complaint

> **Customer Complaint:**  
> *"A developer reported that some time last week, the documentation assistant gave a Python code sample using a method we deprecated. No trace ID, no user ID, no package version was provided."*

This is the classic production debugging challenge: an unindexed, vague customer report against high-throughput production traffic. The assistant answers hundreds of queries daily, and unversioned requests default to the latest SDK version (v3).

---

## 2. Timed Incident Hunting & Log Slicing Audit

### 2.1 Investigation Stopwatch Summary
* **Search Stopwatch Result:** **`04:38`** (`mm:ss`)  
* **Target Constraint:** Under 5 minutes (`05:00`)  
* **Result Verdict:** **PASSED (`04:38` < `05:00`)**  
* **Isolated Trace ID:** **`tr_prod_20261016_8831f4`**  
* **Verification Sign-off:** Alex Rivera (Staff SRE / Observability Lead)

```
00:00 ─── Time Window Slice (Oct 14 - Oct 20) ──────────────> 1,252 traces
01:10 ─── Query Input String Regex Search ("deprecated") ────> 0 matches (Dev asked benign question)
02:30 ─── Status Code & Error Slice (status != 200) ──────────> 0 matches (Silent correctness bug)
03:15 ─── Cost Outlier Slice (> 99th percentile) ────────────> 0 matches ($0.00178 is normal cost)
04:38 ─── Unindexed Full-Text Scan of Output Code Blocks ────> HIT: tr_prod_20261016_8831f4
```

### 2.2 Slicing Strategy & Investigative Trajectory
1. **Time Window Slice (00:00 - 01:10):**  
   Scoped production logs to the 7-day window from `2026-10-14T08:00:00Z` to `2026-10-20T23:59:59Z`.  
   *Candidate pool:* **1,252 production traces**.
2. **Input Query Text Filtering (01:10 - 02:30):**  
   Attempted keyword searches over `query` for `"deprecated"`, `"legacy"`, `"v2"`, and specific deprecation names (`"Stream.feed"`).  
   *Result:* **0 hits**. The developer did *not* ask about deprecated methods; their prompt was benign:  
   *`"How do I connect and consume real-time telemetry updates in Python?"`*
3. **HTTP Status & Error Slicing (02:30 - 03:15):**  
   Filtered by `status_code != 200` to find 5xx/4xx errors.  
   *Result:* **0 hits**. The LLM successfully synthesized executable code and returned HTTP 200 OK. The error was purely a semantic/correctness defect.
4. **Cost Outlier Filtering (03:15 - 03:45):**  
   Ranked requests by `total_cost_usd` descending to detect token runaways.  
   *Result:* The query consumed 741 tokens and cost **$0.00178**, perfectly within the p50 band.
5. **Output Payload Slicing (03:45 - 04:38):**  
   Ran an unindexed full-text regex scan against the deprecation symbol catalog (`data/deprecations.json`) across the `output_code` and `output_text` strings of all 1,252 traces.  
   *Result:* Matched trace **`tr_prod_20261016_8831f4`** on `Stream.feed`.

### 2.3 Honest Observability Audit: Why Did the Hunt Burn 4 Minutes 38 Seconds?
The investigation consumed 4 minutes and 38 seconds due to a critical gap in our legacy telemetry schema:
* **The Root Cause of Delay:** In the legacy schema, our log pipeline indexed only request inputs (`user_id`, `query`, `status_code`, `total_latency_ms`). **Generated output code snippets were treated as opaque markdown blobs with zero AST parsing, zero symbol tokenization, and no inverted index.**
* Searching inputs when the user complaint is about generated outputs forces the on-call engineer into sequential regex scans across gigabytes of raw JSONL payloads.
* **The Missing Log Field:** **`deprecated_symbol_emitted`** (boolean) and **`emitted_symbols`** (string array). Had these fields been extracted at generation time and indexed, an on-call engineer would have found the trace in **19 seconds** via `filter: deprecated_symbol_emitted == true`.

---

## 3. Full Isolated Trace Summary (`trace.json`)

* **Trace ID:** `tr_prod_20261016_8831f4`  
* **Timestamp:** `2026-10-16T14:22:18.412Z`  
* **User ID:** `usr_dev_4821`  
* **User Query:** *"How do I connect and consume real-time telemetry updates in Python?"*  
* **Active Prompt Version:** `v1.2.0`  
* **HTTP Status:** `200 OK`  
* **Retrieved Context Chunk IDs:** `["v2_stream_v2_struct_000", "v2_stream_v2_struct_001"]`

```json
{
  "trace_id": "tr_prod_20261016_8831f4",
  "prompt_version": "v1.2.0",
  "retrieved_context_ids": ["v2_stream_v2_struct_000", "v2_stream_v2_struct_001"],
  "spans": {
    "retrieval": { "latency_ms": 124.5, "input_tokens": 16, "output_tokens": 412, "cost_usd": 0.000620 },
    "generation": { "latency_ms": 1180.2, "prompt_tokens": 580, "completion_tokens": 145, "cost_usd": 0.001160 },
    "tools": { "latency_ms": 45.3, "cost_usd": 0.000000, "tool_calls": ["check_deprecation"] }
  },
  "total_latency_ms": 1350.0,
  "total_tokens": 741,
  "total_cost_usd": 0.001780
}
```

### Retrieval vs. Hallucination Diagnosis
> **Crucial Finding:** Did the model hallucinate from pre-trained memory, or did retrieval serve obsolete documentation?  
> **Verdict: Retrieval served obsolete documentation.**  
> The trace records `retrieved_context_ids: ["v2_stream_v2_struct_000", "v2_stream_v2_struct_001"]`, which originate from `data/v2/stream_v2.md`. Because the hybrid retrieval pool was unpartitioned and lacked a strict `sdk_version == "v3"` filter for unversioned queries, the vector search retrieved legacy v2 documentation for real-time telemetry. The LLM faithfully grounded its response in the retrieved context, synthesizing `Stream.feed(channel="telemetry", buffer_len=1024, ping_interval=5000)`. Logging chunk IDs transformed what would have been a 2-day hallucination mystery into a 10-second root cause diagnosis.

---

## 4. The Failure-to-Test Loop: RED -> GREEN

### 4.1 Creating the Permanent Eval Case (`tests/test_deprecation_eval.py`)
We codified the customer incident into a permanent test case (`test_case_11_customer_incident_telemetry_stream`) alongside the 10 baseline cases in our core test suite:
* **Input Query:** *"How do I connect and consume real-time telemetry updates in Python?"*
* **Assertion 1 (Syntax):** Must parse valid Python AST via `ast.parse`.
* **Assertion 2 (Deprecation):** Must NOT contain `Stream.feed`, `buffer_len`, `ping_interval`, or any deprecated symbol from `data/deprecations.json`.
* **Assertion 3 (Modern Target):** Must use active v3 symbols (`Stream.subscribe`, `max_buffer_size`, `keep_alive_ping_ms`).
* **Assertion 4 (Context Alignment):** Grounded chunk IDs must belong strictly to v3 (`v3_stream_v3_struct_000`), never v1/v2.

### 4.2 RED Run (Before Fix — Prompt `v1.2.0`)
Executing the suite before applying any code fixes demonstrates that the existing 10 tests pass, but the new customer incident case reliably fails:

```
[EVAL SUITE] Initialized with Prompt Version: v1.2.0
..........F
======================================================================
FAIL: test_case_11_customer_incident_telemetry_stream (tests.test_deprecation_eval.TestDeprecationEvaluationSuite)
q11: Customer Incident (Week 11 Drill).
----------------------------------------------------------------------
Traceback (most recent call last):
  File "tests/test_deprecation_eval.py", line 142, in test_case_11_customer_incident_telemetry_stream
    res = self._evaluate_case(incident_query)
  File "tests/test_deprecation_eval.py", line 56, in _evaluate_case
    self.assertTrue(no_dep_ok, f"Deprecation Violation: {no_dep_msg}")
AssertionError: False is not true : Deprecation Violation: Contains deprecated token/method matching pattern '\bStream\.feed\b': matched 'Stream.feed'

----------------------------------------------------------------------
Ran 11 tests in 0.006s

FAILED (failures=1)
Pass Count: 10/11 passed (1 FAILED) --> RED
```

### 4.3 Implementing the Layered Fix
1. **Prompt Version Bump (`v1.2.0` -> `v1.3.0`):**
   Updated system prompt in `src/production_agent.py` to inject strict negative constraints:
   ```
   You are the Production SDK v3 Assistant (v1.3.0).
   CRITICAL GUARDRAIL: Never emit deprecated methods (e.g., Stream.feed, buffer_len, ping_interval,
   Batch.dispatch, Auth.login session_expiry). Always use active v3 equivalents
   (Stream.subscribe, max_buffer_size, keep_alive_ping_ms, Batch.submit_jobs, /v3/auth/token).
   Validate all code against v3 OpenAPI specifications and deprecation registry.
   ```
2. **Retrieval Layer Partitioning (`src/retriever.py` / `src/production_agent.py`):**
   Enforced strict `filter_dict={"sdk_version": "v3"}` so archived legacy files (`data/v1/` and `data/v2/`) are permanently excluded from unversioned production queries.
3. **Telemetry Pipeline Guard:**
   Automated AST symbol extraction and real-time validation via `assert_no_deprecated_symbols`.

### 4.4 GREEN Run (After Fix — Prompt `v1.3.0`)
Re-running the full suite proves that the customer incident passes and caused **zero regressions** across the other 10 test cases:

```
[EVAL SUITE] Initialized with Prompt Version: v1.3.0
...........
----------------------------------------------------------------------
Ran 11 tests in 0.005s

OK
Pass Count: 11/11 passed (0 FAILED, ZERO REGRESSIONS) --> GREEN
```

---

## 5. Deployment Safety & Rollback Plan

### Prompt Version Bump
* **Current Production Version:** `v1.2.0`
* **New Target Version:** `v1.3.0` (Includes negative deprecation guardrails and v3-only retrieval partition)

### Two-Line Canary Deployment & Rollback Strategy
1. **Canary Deployment:**  
   *Route 5% of production traffic to prompt `v1.3.0` via edge feature flag `sdk_prompt_v1_3_0`, continuously monitoring the telemetry metric `deprecated_symbol_emitted` and p99 latency across a 30-minute burn-in window.*
2. **Automated Rollback:**  
   *If the canary emits any deprecated symbol (`deprecated_symbol_emitted > 0`) or if p99 latency exceeds 2,500ms, the router circuit breaker immediately forces the feature flag to 0% in under 5 seconds with zero container restarts.*

---

## 6. Bonus Challenge: Wire the Drill Shut

### 6.1 Telemetry Pipeline Hardening
To eliminate lookup delays permanently, we added two new fields to every production trace span in `src/telemetry.py`:
1. `deprecated_symbol_emitted` (`bool`): Evaluated via deterministic AST regex against `data/deprecations.json` during the generation span.
2. `emitted_symbols` (`list[str]`): Inverted-index token list of all SDK methods and parameter names present in the output.

### 6.2 Second Timed Drill (Plant & Beat)
Squadmate Alex planted a second bad response in our production logs:
* **Trace ID:** `tr_prod_20261019_9942a1` (Planted on Monday, Oct 19, 2026)
* **User Query:** *"How do I authenticate and configure session expiration time in Python?"*
* **Defect:** Synthesized deprecated `Auth.login(username="...", session_expiry=3600)` instead of v3 JWT token TTL.

### 6.3 Performance Comparison
We executed the hunt using the new indexed telemetry filter `deprecated_symbol_emitted == true`:

| Drill | Defect Planted | Log Slicing Strategy | Missing Field | Time-to-Find (`mm:ss`) | Speedup |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Drill 1 (Baseline)** | `Stream.feed` in code | Unindexed full-text scan over output strings | `deprecated_symbol_emitted` | **04:38** | Baseline |
| **Drill 2 (Bonus)** | `Auth.login.session_expiry` | Indexed filter: `deprecated_symbol_emitted == true` | None (Field added) | **00:19** | **93.2% faster (Saved 4m19s)** |

**The One Field That Closed the Gap:**  
**`deprecated_symbol_emitted: true`** — By moving deprecation detection into the ingestion span of our telemetry pipeline and indexing the boolean outcome, log hunting time plummeted from nearly 5 minutes down to 19 seconds.
