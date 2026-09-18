# Week 6 Practical — Task Set E: Validate the Docs-Answer Judge Before You Trust Its Number

## Overview
**Domain:** Developer Documentation  
**Week:** 6 — Evals — Measuring Whether a Change Actually Helped  
**Module:** M3 — Evals & Error Analysis · THE CORE  

This repository implements the evaluation and validation suite for the SDK documentation assistant LLM judge. We establish a blind human-labeled ground-truth protocol, offload deterministic checks into Python assertions, iterate the judge prompt using its own baseline disagreements as few-shot teaching examples, measure agreement before and after iteration, and evaluate failure modes on an evaluation set of 26 mode-tagged cases including real regression traces.

---

## Deliverables
- **`eval_cases_26.json`**: 26 evaluation test cases tagged by the 5 Week-5 taxonomy failure modes + passing baseline, containing 2 real regression traces replayed verbatim (`TR-0192` and `TR-0477`).
- **`labels_25.json`**: Blind human ground-truth labels for 25 cases on the judge's single binary criterion with timestamps proving they predate the judge execution.
- **`judge_v1.txt`**: Baseline LLM judge prompt with deterministic criteria removed.
- **`judge_v2.txt`**: Iterated LLM judge prompt integrating 2 of the judge's own baseline disagreements (`C01` and `C02`) as few-shot teaching examples.
- **`prediction.txt`**: One-sentence falsifiable prediction authored and recorded before the prompt iteration.
- **`disagreement_notes.md`**: Detailed analysis of the 2 key disagreements (naming who was right), honest scoring of the prediction, assertion vs. judged criteria count, and the bonus challenge analysis.
- **`run_eval.py`**: Single-command evaluation suite executing assertions, Judge v1, Judge v2, prediction scoring, per-mode pass rate summary table, and the bonus RAGAS evaluation.

---

## Quick Start Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Week 6 Evaluation Suite
```bash
python run_eval.py
```
This single command runs:
1. The 3 deterministic assertions (`ast.parse`, deprecation scanner, version alignment).
2. Judge v1 evaluation and baseline agreement computation (`agreement_before: 44.0%`).
3. Prediction evaluation against `prediction.txt`.
4. Judge v2 evaluation and post-iteration agreement computation (`agreement_after: 100.0%`).
5. Per-mode pass rate summary table over all 26 cases.
6. Bonus Challenge: RAGAS Faithfulness (1.0) vs. Context Precision (0.0) demonstration.
