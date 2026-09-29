# Agent Failure Modes Taxonomy — Trajectory Evaluations & Reliability Testing

**Domain:** Developer Documentation & Migration Agents (SDK v1 / v2 / v3)  
**Evaluation Scope:** 10 Structured Migration Queries across 3 API Versions  
**Framework:** Trajectory-Based Telemetry & Semantic Path Validation  

---

## Executive Summary

Standard outcome-based evaluation ("did the agent output valid code?") fails to detect silent architectural failures. An agent that emits valid v3 code simply by reciting it from pre-trained memory rather than executing the spec-lookup tool creates an **Outcome-vs-Trajectory Gap**. When API schemas change in production, ungrounded agents break silently.

This taxonomy categorizes the primary trajectory failure modes observed in autonomous tool-calling documentation agents.

---

## Ranked Failure Mode Taxonomy

| Mode ID | Failure Mode Name | Frequency (Baseline) | Severity | Root Cause | Example Trace ID |
| :---: | :--- | :---: | :--- | :--- | :---: |
| **FM-1** | **Tool Bypass (Shortcut Memorization)** | **30.0%** (3/10) | **CRITICAL** (Ticking clock: False positive pass) | Parametric memory hallucination bypassing source-of-truth spec lookup | `q7`, `q9`, `q10` |
| **FM-2** | **Hallucinated / Invalid Tool Argument** | **10.0%** (1/10) | **HIGH** (Tool execution failure / 404 response) | Outdated schema assumptions; passing legacy paths to v3 tools | `q2` |
| **FM-3** | **Inefficient Looping / Step Overrun** | **10.0%** (1/10) | **MEDIUM** (Inflates latency & runaway Max cost) | Search query divergence; redundant querying without new state | `q4` |
| **FM-4** | **Out-of-Order Tool Sequencing** | **10.0%** (1/10) | **HIGH** (Ungrounded dynamic branching) | Inverting topological dependencies (searching docs before checking spec) | `q5` |
| **FM-5** | **Premature Exit / Incomplete Trajectory** | **0.0%** (0/10) | **HIGH** (Incomplete response) | Early termination prior to gathering sufficient evidence | N/A |
| **PASS** | *Verified Trajectory Adherence* | **40.0%** (4/10) | **NONE** (Ground-truth verified execution path) | Complies with flexible allowed path sets and schema contracts | `q1`, `q3`, `q6`, `q8` |

---

## Detailed Failure Mode Profiles

### FM-1: Tool Bypass (Shortcut Memorization / Hallucination)
- **Description:** The agent skips a mandatory source-of-truth tool call (e.g., `get_openapi_spec`) and recites code directly from pre-trained memory.
- **Why It Is a Ticking Clock:** The agent produces valid code that passes outcome assertions. However, because it never checked the active OpenAPI specification, any silent endpoint change, deprecation, or default parameter shift in production causes immediate outage.
- **Concrete Example (`q10`):**
  - *Query:* "Confirm if `/v3/auth/token` endpoint in OpenAPI spec provides bearer token scopes and what the TTL default is."
  - *Observed Trajectory:* Calls `check_deprecation` $\rightarrow$ Skips `get_openapi_spec` $\rightarrow$ Synthesizes answer directly from parametric memory.
  - *Result:* Outcome PASS (code has `token_ttl_sec=3600`), Trajectory FAIL (never inspected OpenAPI spec).

---

### FM-2: Hallucinated / Invalid Tool Arguments
- **Description:** The agent selects the correct tool but passes hallucinated endpoints, non-existent parameter names, or invalid version strings.
- **Concrete Example (`q2`):**
  - *Query:* "We are upgrading `Auth.login` from v2 to v3. What is the new endpoint and token expiration parameter?"
  - *Observed Tool Call:* `get_openapi_spec(endpoint="/v3/auth/login", version="v3")`
  - *Error:* `/v3/auth/login` does not exist in v3; the v3 endpoint is `/v3/auth/token`.
  - *Result:* Tool returns `404 Not Found`, forcing degraded synthesis.

---

### FM-3: Inefficient Looping / Step Overrun
- **Description:** The agent repeats tool calls with minimal lexical permutations, burning execution budgets without acquiring novel evidence.
- **Concrete Example (`q4`):**
  - *Query:* "Migrate `Batch.dispatch` to v3: Inspect OpenAPI spec for `/v3/batch/submit_jobs`..."
  - *Observed Trajectory:* Calls `check_deprecation` $\rightarrow$ `get_openapi_spec` $\rightarrow$ `search_docs("Batch")` $\rightarrow$ `search_docs("Batch submit_jobs retry concurrency")` (takes 4 steps instead of optimal 3).
  - *Cost Variance Impact:* Inflates worst-case query cost to **$0.002619** (+56.9% higher than median p50 of $0.001669).

---

### FM-4: Out-of-Order Tool Sequencing
- **Description:** On queries requiring dynamic branching based on API schema specifications, the agent executes downstream tools before checking prerequisite evidence.
- **Concrete Example (`q5`):**
  - *Query:* "Migrate `Config.get_config` to v3: Check if OpenAPI spec supports `strict_validation` and `env_override`..."
  - *Observed Trajectory:* Calls `check_deprecation` $\rightarrow$ `search_docs("Config load_settings strict YAML")` $\rightarrow$ `get_openapi_spec`.
  - *Flaw:* The docs query was guessed before the OpenAPI spec was verified, violating causal conditioning.

---

### FM-5: Premature Exit / Incomplete Trajectory
- **Description:** Agent exits loop after a single step without gathering requisite context or documentation evidence.
- **Status in Test Suite:** 0 instances observed across baseline and mitigated runs.
