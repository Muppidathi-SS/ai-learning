# Week 5 Practical — Task Set E: Reading Traces Like a Professional

## Overview
**Domain:** Developer Documentation  
**Week:** 5 — Error Analysis — Reading Traces Like a Professional  
**Module:** M3 — Evals & Error Analysis · THE CORE  

This project implements error analysis and trace inspection for an SDK documentation assistant that accumulated over 1,000 production traces. We draw a seeded random sample of 20 traces, verify trace replayability, perform honest open-coding with zero code fixes, cluster observations into a ranked failure taxonomy, formulate a dated falsifiable prediction, and analyze team blind spots via the bonus demo-set evaluation.

---

## Deliverables
- **`taxonomy.md`**: One-page ranked failure taxonomy fitting on a single screen with 5 named failure modes, counts, frequency percentages, severity ratings, and example trace IDs.
- **`notes.md`**: Complete evaluation report containing:
  - Seeded random sample details (`seed = 42`) and all 20 sampled trace IDs
  - 20 verbatim open-coding observation sentences (no category labels or premature diagnoses)
  - Trace replay evidence for trace `TR-0229` showing 100% bit-for-bit equivalence from trace data alone
  - Reconstructed schema fields audit (`prompt_version`, `retrieved_chunks` with scores/content, `model_params`, `raw_output`)
  - Dated falsifiable prediction (`2026-09-16`) with expected quantitative deltas
  - 3-sentence public benchmark critique
  - Bonus Challenge: Demo set vs. random sample top-mode frequency comparison and team confirmation bias analysis.
- **`traces.jsonl`**: 1,050 full-schema production traces logged across developer queries.
- **`run_week5.py`**: Evaluation runner reproducing seeded sampling, trace replay verification, and bonus analysis.
- **`generate_traces.py`**: Generation script used to simulate the week's production traffic across the corpus.

---

## Quick Start Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Week 5 Evaluation Runner
```bash
python run_week5.py
```
This script loads `traces.jsonl`, draws the 20 seeded traces (`seed = 42`), performs deterministic replay of trace `TR-0229`, prints side-by-side verification, and computes the bonus challenge metrics.
