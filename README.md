# Week 9 Practical — Task Set E: Bolt on the Package-Registry Server

## Overview
- **Domain:** Developer Documentation
- **Week:** 9 — MCP — The Standard Way Agents Reach Tools & Data
- **Module:** M5 — MCP, Multi-agent & A2A
- **Core Objective:** Prove dynamic tool discovery by bolting on DevRel's `package-registry` MCP server with zero code changes in the agent module.

---

## Deliverables & Submission Checklist

| Item | File | Description |
| :--- | :--- | :--- |
| **1. Agent Diff** | [`agent_diff.txt`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/agent_diff.txt) | Proves **ZERO lines changed** in `src/agent.py` between server 1 and server 1+2. |
| **2. Config Diff** | [`config_diff.txt`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/config_diff.txt) | Shows the configuration diff adding the second server (`mcp_config.json`). |
| **3. Wire Protocol** | [`wire.json`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/wire.json) | Hand-annotated raw JSON-RPC `initialize` -> `tools/list` -> `tools/call` capture and model-call statement. |
| **4. Tool Count Line** | Console & Summary | `3 before -> 6 after, with tool names: [search_docs, get_openapi_spec, check_symbol_deprecation] -> [search_docs, get_openapi_spec, check_symbol_deprecation, get_package_versions, get_deprecation_notice, get_release_metadata]` |
| **5. Error Recovery** | [`error_before_after.md`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/error_before_after.md) | Docstring rewritten as prompt and before/after transcript of model recovering from failed version lookup. |
| **6. Supply-Chain Risk** | [`risk_note.md`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/risk_note.md) | Exactly 5 lines answering who wrote it, what it reaches, what it logs, what a stolen token could do, and ship/don't. |
| **7. Bonus Gateway** | [`src/mcp/gateway.py`](file:///c:/Users/uttam/Documents/GIT%20PROJECTS/ai-learning/src/mcp/gateway.py) | Front-door gateway with fan-out, single-line audit logging, and scoped token authorization. |

---

## Quick Start & Running the Output File

To run the complete Week 9 suite:
```bash
python run_week9.py
```

To run automated unit tests:
```bash
python tests/test_week9.py
```
