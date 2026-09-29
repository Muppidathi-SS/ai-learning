# Week 8 Engineering Challenge: Agent Failure Modes & Trajectory Evals

## Overview
- **Domain:** Developer Documentation & Migration Agents
- **Week:** 8 — Agent Failure Modes & Trajectory Evals
- **Module:** M4 — Agents & Trajectory Evaluations
- **Core Focus:** Exposing and closing the Outcome-vs-Trajectory Gap, single mitigation experiments, and indirect prompt injection defense.

---

## Key Deliverables Summary

| Deliverable | File Path | Description |
| :--- | :--- | :--- |
| **1. Trajectory Eval Suite** | [`trajectory_eval.py`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/trajectory_eval.py) | Comprehensive CLI runner executing 10 queries with flexible path sets. |
| **2. Trajectory Metrics Engine** | [`src/trajectory_engine.py`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/src/trajectory_engine.py) | Telemetry engine computing Tool-Choice Accuracy, Argument Validity, Step Efficiency, and Cost (p50 & Max). |
| **3. Test Specification** | [`data/test_cases_w8.json`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/data/test_cases_w8.json) | 10 migration test queries with allowed path sets, optimal steps, and mandatory tools. |
| **4. Failure Mode Taxonomy** | [`taxonomy.md`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/taxonomy.md) | Formal taxonomy of failure modes (FM-1 to FM-5) with severity, root cause, and examples. |
| **5. Mitigation & Gap Report** | [`eval_report_w8.md`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/eval_report_w8.md) | Full engineering report detailing gap calculation (60.0%), exposed trace (`q10`), mitigation delta (-3), regression matrix, and injection defense. |
| **6. Prompt Injection Defense** | [`src/injection_defense.py`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/src/injection_defense.py) | 3-layer defense (ToolSanitizer, ScopeManager, SecurityCodeGuardrail) against indirect prompt injection. |
| **7. Automated Unit Tests** | [`tests/test_trajectory_eval.py`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/tests/test_trajectory_eval.py) & [`tests/test_injection_defense.py`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/tests/test_injection_defense.py) | Unit tests verifying flexible path assertions, argument validation, and security guardrails. |

---

## Quick Start Instructions

### 1. Run the Full Week 8 Evaluation Suite
```bash
python trajectory_eval.py
```
This executes:
1. Baseline agent evaluation across 10 queries using flexible path assertions.
2. Trajectory Metrics Engine telemetry:
   - Tool-Choice Accuracy: **84.62%**
   - Argument Validity Rate: **96.15%**
   - Step Efficiency: **Actual/Optimal = 0.9286 | Optimal/Actual = 1.0769**
   - Cost Distribution: **p50 = $0.001669 | Max = $0.002619** (worst-case variance: +56.9%)
3. Outcome-vs-Trajectory Gap calculation: **100.0% - 40.0% = 60.0%**.
4. False Positive trace expose on query `q10` (auth session token migration).
5. Single Targeted Mitigation experiment (Mandatory Spec Grounding Contract):
   - FM-1 Before $\rightarrow$ After: **3 $\rightarrow$ 0 (-100% reduction)**.
   - Gap reduced from **60.0% $\rightarrow$ 30.0%**.
   - Price Paid measured: **+98 tokens/q, +$0.000159/q, +0.0ms p50 latency**.
6. Per-Mode Regression Matrix audit (0 regressions, 0 new failure modes).
7. Bonus Challenge: Indirect prompt injection attack simulated inside community docs comments and 100% neutralized by 3-layer defense.

### 2. Run Automated Verification Tests
```bash
python tests/test_trajectory_eval.py
python tests/test_injection_defense.py
```

### 3. Verify Week 7 Race Backward Compatibility
```bash
python run_race.py
python tests/test_bonus_memory.py
```

---

## Week 7 Reference (Preserved)
- **`run_race.py`**: Races docs agent against fixed 3-step workflow.
- **`race.csv`**: Comparison metrics across fixed workflow vs agent loop.
- **`budget_termination.log`**: Proof of all 4 budget limit terminations.
- **`verdict.md`**: Architectural decision rule verdict (<150 words).
