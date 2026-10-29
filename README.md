# Week 12 Capstone — SDK Docs Answer Engine (Integration & Defense)

[![Architecture](https://img.shields.io/badge/Architecture-RAG%20%2B%20Agent%20%2B%20MCP-blue.svg)](architecture.md)
[![Evals](https://img.shields.io/badge/Evals-32%2F32%20Passing-success.svg)](eval_report.md)
[![Judge Agreement](https://img.shields.io/badge/Judge%20Agreement-100%25%20(n%3D32)-brightgreen.svg)](eval_report.md)
[![Trajectory Gap](https://img.shields.io/badge/Trajectory%20Gap-8.3%25-orange.svg)](trajectory_eval.md)
[![PII Protection](https://img.shields.io/badge/PII%20Sanitization-Redact--on--Write-blueviolet.svg)](trace.json)

**Domain:** Developer Documentation & SDK Migration Assistant  
**Variant:** Variant E  
**Integrator Fleet:** ~9,000 active developers (40% on legacy `v2.x` LTS, 60% on `v3.0`)  
**Core Deliverable:** An answer engine that resolves caller SDK version before retrieval, surfaces unasked deprecation warnings, provides clickable versioned citations, and deterministically verifies that every emitted code sample compiles and runs.

---

## 1. Quick Start (Single-Command Execution)

A stranger can clone this repository and run the complete end-to-end integrated system, tests, and checks with **one command**:

```bash
python3 run_capstone.py
```

### What this single command executes:
1. **Corpus & Version Partition Validation:** Verifies dual live reference docs (`data/v2` and `data/v3`), `CHANGELOG.md`, `docs/migration_guide.md`, 200 runnable code samples (`data/code_samples_200.json`), and 50 Stack Overflow questions.
2. **Live Integrator Run (v2.4 Caller):** Demonstrates version resolution before retrieval, valid runnable `client.query` code, version-tagged citations, and unasked deprecation warning.
3. **Live Migration Run (v3.0 Caller):** Demonstrates plain statement on removed methods (*"that method no longer exists in 3.0, here is the migration"*) and mandatory `timeout=30` enforcement in `Client.search()`.
4. **Live MCP Protocol Hop:** Independent JSON-RPC 2.0 handshake and live tool calls by external squad client (Maya Patel from Squad B).
5. **Closed Failure-to-Test Loop:** Demonstrates failure in `MODE=RED` (unpartitioned retrieval) vs success in `MODE=GREEN` (hardened pipeline with zero regressions).
6. **32-Case Integrated Evaluation Suite:** Deterministic AST syntax and symbol-table checks before judges.
7. **Validated LLM Judge Agreement:** Re-checks judge agreement against ground-truth hand labels (**100.0% agreement**, clearing $\ge 85\%$).
8. **Trajectory Evaluation & Gap:** Evaluates multi-hop tool-choice accuracy (**96.8%**) and reports the honest outcome-vs-trajectory gap (**8.3%**).
9. **Stack Overflow Phrasing Ablation:** Quantifies hit-rate recall loss when Stack Overflow real-world vocabulary is dropped.
10. **Unified Trace Export (`trace.json`):** Verifies single trace ID surviving all spans and PII redact-on-write.

---

## 2. Running Individual Capabilities

### A. Run Full Integrated Evaluation Suite
```bash
python3 -m unittest tests/test_integrated_eval.py
```
*Expected Output: `Ran 32 tests in 0.024s ... OK` (32/32 passed).*

### B. Run Closed-Loop Failure (RED State)
```bash
MODE=RED python3 -m unittest tests/test_integrated_eval.py
```
*Expected Output: `FAILED (failures=1)` — proves reproduction of the customer incident (`Client.search does not exist in SDK v2.x`).*

### C. Run Third-Party Fresh-Eyes MCP Review Client
```bash
python3 -m src.mcp.external_client
```
*Expected Output: Squad B external reviewer client executes dynamic tool discovery and tool calls over JSON-RPC 2.0 with 100% conformance.*

---

## 3. Submission Checklist & Artifact Directory

All 10 required Capstone artifacts are delivered and documented in this repository:

| Requirement / Deliverable | File | Description |
| :--- | :--- | :--- |
| **1. Single-Command Entry Point** | [`run_capstone.py`](run_capstone.py) | Verified one-command pipeline executing live runs, MCP, evals, and trajectory analysis. |
| **2. Tuesday's Seam List (Unedited)** | [`tuesday_seams.md`](tuesday_seams.md) | 8 seams identified on Day 2: 5 marked FIXED, 2 ACCEPTED, 1 RAN-OUT-OF-TIME. |
| **3. One-Page Architecture Sketch** | [`architecture.md`](architecture.md) | Boxes, arrows, model calls, token costs, and stage dollar attribution. |
| **4. Integrated Eval Suite Report** | [`eval_report.md`](eval_report.md) | 32 cases ($n=32$), named metric moved (-18.8% wrong-version code), judge agreement (100%), and stated non-coverage. |
| **5. Re-Scored Error Taxonomy** | [`taxonomy.md`](taxonomy.md) | 5 modes with frequencies and trace IDs; deep-dive on new integration mode (`INTEGRATION_MCP_VERSION_DESYNC`). |
| **6. Trajectory Evaluation & Gap** | [`trajectory_eval.md`](trajectory_eval.md) | Tool-choice accuracy (96.8%) and honest outcome-vs-trajectory gap (8.3%). |
| **7. Unified End-to-End Trace** | [`trace.json`](trace.json) | Single trace ID (`tr_sdk_...`) surviving agent hop + MCP hop, latency/cost per span, PII line held. |
| **8. Top 3 Known Weaknesses** | [`top3_weaknesses.md`](top3_weaknesses.md) | Dated Wednesday, unprompted: AST chunk splitting, MCP pipe buffer, version comparative ambiguity. |
| **9. 10x Scale Bottleneck Plan** | [`scale_10x.md`](scale_10x.md) | Cost per question ($0.001894), 10x bottleneck (250k TPM rate limit breached at 305 QPM / 4.06x), and v3.1 defense. |
| **10. Fresh-Eyes Review Note** | [`fresh_eyes_review.md`](fresh_eyes_review.md) | External audit by Maya Patel (Squad B Lead): where she stumbled, and what we changed. |
| **11. 10-Minute Demo Script** | [`demo_script.md`](demo_script.md) | Timed 4-part demo standard: The Real Run, The Failures Found, A Number That Moved, and What's Next. |

---

## 4. Key Architectural Defenses (Hostile Questions)

1. **"Does your retriever filter on version, or just have version numbers in the text?"**
   - The retriever strictly filters on metadata: `sdk_version == caller_version`. It never mixes v2 and v3 chunks. Citations explicitly name the SDK version: `[client_v2.md (SDK v2.x)](data/v2/client_v2.md#L1-L30)`.
2. **"Does anything actually check that code parses and methods exist in that version?"**
   - Yes (**Bonus Challenge Delivered**). Every code block is parsed through Python `ast.parse` and checked against `data/symbol_table.json`. Emitting `client.search()` to a v2 caller or `client.query()` to a v3 caller fails deterministically before emission.
3. **"Why keep Stack Overflow answers in your corpus if they are dead in v3?"**
   - They provide the long-tail colloquial phrasings developers actually type. Dropping them causes an 18.7% hit-rate recall loss. By using them strictly for embedding vocabulary expansion and filtering through version metadata, we gain the phrasings without emitting dead APIs.
4. **"What breaks first at 10x in-IDE scale?"**
   - The **LLM Token Rate Limit (250,000 TPM ceiling) breaks first at 305 queries/minute (4.06x baseline)**. Monthly cost ($55k/mo) and latency (860ms) remain well within budget and SLA thresholds.
