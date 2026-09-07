# Week 3 Practical — Task Set E: SDK v3 Documentation RAG & Chunking Benchmark

## Problem Statement Overview
The **v3 SDK release** landed with 6 new reference documentation pages (`client_v3.md`, `auth_v3.md`, `batch_v3.md`, `config_v3.md`, `stream_v3.md`, `webhook_v3.md`). Each page contains parameter tables (`Parameter`, `Type`, `Default`, `Required`) wrapped in prose and fenced code samples.

This repository tests whether your chunking strategy preserves parameter defaults (e.g. `retry_backoff_ms`) attached to their parent methods (e.g. `Client.send()`) or cuts code fences and table rows mid-line.

---

## Directory Structure
```
week-3-task/
├── docs/
│   ├── v2/
│   │   └── client_v2.md          # Legacy v2 SDK reference page
│   └── v3/
│       ├── auth_v3.md            # v3 Auth reference page
│       ├── batch_v3.md           # v3 Batch reference page
│       ├── client_v3.md          # v3 Client reference page
│       ├── config_v3.md          # v3 Config reference page
│       ├── stream_v3.md          # v3 Stream reference page
│       └── webhook_v3.md         # v3 Webhook reference page
├── src/
│   ├── __init__.py
│   ├── chunkers.py               # Strategy 1 (Naive Fixed-Size) & Strategy 2 (Structure-Aware Markdown)
│   ├── indexer.py                # Embedding vector index builder (MiniLM-L6-v2)
│   ├── retriever.py              # Similarity retriever with metadata filters
│   └── generator.py              # Grounded response generator with refusal logic
├── run_pipeline.py               # Main evaluation benchmark engine
├── results.md                    # Primary deliverable (Submission Report)
├── requirements.txt              # Project dependencies
└── README.md                     # Documentation
```

---

## Quick Start Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Evaluation Benchmark Pipeline
```bash
python3 run_pipeline.py
```
This runs the full benchmark across 8 known-answer queries, evaluates Hit-in-Top-5 performance for Naive vs. Structure-Aware chunkers, demonstrates metadata filtering (`sdk_version='v3'`), tests refusal behavior on 3 out-of-corpus queries, and outputs the final submission report to **`results.md`**.
