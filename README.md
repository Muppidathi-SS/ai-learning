# Week 10 Engineering Challenge: Multi-Agent Systems & Agent-to-Agent (A2A) Protocols

## Overview
- **Domain:** Developer Documentation & SDK Migration
- **Week:** 10 — Multi-Agent Systems & Agent-to-Agent (A2A) Protocols
- **Module:** M5 — MCP, Multi-Agent & A2A
- **Core Objective:** Conduct an honest, telemetry-backed experiment: build a **Manager-Plus-Two-Specialists Team** (Orchestrator delegating to a `VersionDeprecationWorker` and a `CodeSampleWorker`) and race it head-to-head against the **Single Agent** across 10 evaluation test cases.

---

## Deliverables & Artifacts Matrix

| Deliverable | File | Description |
| :--- | :--- | :--- |
| **1. Race Table** | [`race_table.md`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/race_table.md) | Head-to-head comparison of 4 metrics $\times$ 2 arms across the 10 evaluation test cases. |
| **2. Delegation Handoff Log** | [`handoffs.log`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/handoffs.log) | Structured log recording every agent-to-agent hop, input/output tokens, cost, latency, and status. |
| **3. Context Multiplier & Bottleneck** | In `race_table.md` & console | Context Re-Send Multiplier ($1.6\times$) and dominant handoff step identified (`orchestrator -> code-sample worker resend`, 53.5% of tokens). |
| **4. Injected Failure Report** | [`failure_case.md`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/failure_case.md) | Detailed analysis of injected HTTP 500 error on Worker 1, verifying retry loop, graceful degradation, and hallucination prevention. |
| **5. KEEP or KILL Decision** | [`verdict.md`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/verdict.md) | Exactly 10 lines, citing $\ge 2$ telemetry numbers, explicitly naming and rejecting sunk-cost bias. |
| **6. AgentCard Specification** | [`agent_card.json`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/agent_card.json) | Capabilities, input/output JSON schemas, and Bearer token auth interface contract for the Orchestrator. |
| **7. A2A Protocol & State Machine** | [`a2a_protocol.md`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/a2a_protocol.md) | State diagram mapping HTTP 500 onto `PAUSED: input-required` lifecycle and a 2-line Protocol Value statement. |

---

## 4 Core Telemetry Metrics (Head-to-Head Race)

| Metric | Single Agent (Arm A) | Orchestrator Squad (Arm B) | Performance Delta |
| :--- | :---: | :---: | :---: |
| **Pass Rate (%)** | **100.0%** | **100.0%** | **0.0%** (Identical functional accuracy) |
| **p50 Latency (s)** | **0.0012s** | **0.0019s** | **1.5x slower** (+54.2%) |
| **p99 Latency (s)** | **0.0015s** | **0.0021s** | **1.4x slower** |
| **Total Tokens** | **11,194** | **17,412** | **1.6x Context Re-Send Multiplier** |
| **Cost Per Question ($)** | **$0.001769** | **$0.002772** | **+56.7% cost explosion** |

---

## Quick Start & Verification

### 1. Run the Head-to-Head Race & Generate All Artifacts
```bash
python run_week10.py
```

### 2. Run Automated Regression Test Suite
```bash
python tests/test_week10.py
```
