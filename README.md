# Week 7 Practical — Task Set E: Race the Docs Agent Against a Fixed Workflow

## Overview
- **Domain:** Developer Documentation
- **Week:** 7 — Agent Loops — and When Not to Use Them
- **Module:** M4 — Agents
- **Marks:** 100

This repository implements the comparison suite between an autonomous documentation migration agent and a deterministic 3-step hardcoded workflow for developer SDK migration tasks.

---

## Deliverables & Structure
- **`src/tools.py`**: Implementation of `search_docs`, `get_openapi_spec`, and the new 3rd tool `check_deprecation` with zero description overlap. Uses strongly-typed `ApiVersion` Enum (`v1`, `v2`, `v3`).
- **`src/workflow.py`**: Deterministic 3-step hardcoded pipeline (`check_deprecation` → `get_openapi_spec` → `search_docs` & write sample) sharing identical input and output schemas with the agent.
- **`src/agent.py`**: Autonomous agent loop enforcing all 4 strict budgets (`max_iterations`, `max_tokens`, `max_cost`, `wall_clock_seconds`) with cumulative token accounting (summed across every lap) and clean termination handling.
- **`src/memory.py`**: Bonus Challenge implementation: Sliding window memory with periodic summarization for long threads (30 turns) preserving user constraints across multiple window evictions.
- **`data/openapi_specs.json` & `data/deprecations.json`**: OpenAPI schema definitions and deprecation registry across v1, v2, and v3 APIs.
- **`questions_10.json`**: 10 migration questions, including dynamic branching scenarios where downstream steps depend on OpenAPI spec findings.
- **`run_race.py`**: Single-command race runner executing both systems across all 10 questions, computing the 4 comparison numbers, running budget limit stress tests, and producing `race.csv`.
- **`race.csv`**: Comparison metrics across the 10 questions: Pass Rate (%), p50 Latency (s), Total Tokens (summed over all laps), Cost Per Question ($).
- **`budget_termination.log`**: Log demonstrating that all 4 budgets fired and exited cleanly.
- **`tool_diff.md`**: 3-line git diff of the tool registration alone with zero description overlap explanation.
- **`verdict.md`**: Decision rule verdict under 150 words answering when to use the agent over the workflow, citing the 4 numbers from the race.
- **`notes_w7.md`**: Architectural notes and bonus challenge evaluation.

---

## Quick Start Instructions

### 1. Run the Race & Budget Verification
```bash
python run_race.py
```
This executes:
1. Fixed 3-step workflow across 10 migration questions.
2. Autonomous agent loop across 10 migration questions.
3. Generation of `race.csv` with the 4 key comparison numbers.
4. Enforcement and validation of all 4 budgets in `budget_termination.log`.

### 2. Run the Bonus Challenge Test
```bash
python tests/test_bonus_memory.py
```
Demonstrates that a user's pinned SDK version mentioned in Turn 2 survives into Turn 28 despite 4 sliding window evictions.
