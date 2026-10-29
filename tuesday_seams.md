# Tuesday's Unedited Seam List — SDK Docs Answer Engine

**Context:** Recorded on Tuesday morning (Day 2 of Capstone Week 12) during initial interface integration.  
**Rule:** Unedited from Tuesday's log; each seam marked honestly as `FIXED`, `ACCEPTED`, or `RAN-OUT-OF-TIME`.

---

## Seam Matrix

| Seam ID | Subsystem Interface Boundary | Expected Contract vs Observed Reality | Resolution Status | Technical Rationale & Impact |
| :--- | :--- | :--- | :---: | :--- |
| **SEAM-01** | **Agent Loop ↔ MCP Gateway Version Serialization** | Agent resolved caller version as string `"v2.4"` and passed it verbatim over JSON-RPC. MCP doc server looked up directory `data/v2.4`, which failed because filesystem is partitioned as `data/v2` and `data/v3`. Server failed open to unpartitioned search! | **FIXED** | Added `VersionResolver.normalize()` at both agent and MCP boundaries mapping `"v2.4"` -> `"v2"`. Prevented silent cross-version document leaks. |
| **SEAM-02** | **MCP JSON-RPC Tool Result Deserialization** | Standard MCP protocol encapsulates tool responses in `{"content": [{"type": "text", "text": "{\"results\": [...]}"}]}`. Agent assumed raw Python dictionary return, causing citations and deprecations to evaluate as empty lists. | **FIXED** | Added recursive JSON deserialization in `IntegratedSdkDocsAgent.call_mcp_tool()` to unwrap standard MCP content blocks on the wire. |
| **SEAM-03** | **AST Parse vs Code Markdown Fence Extraction** | Markdown responses containing conversational text with backticks (e.g. `timeout=30`) or malformed python code fences tripped AST parser syntax errors. | **FIXED** | Hardened `SymbolTableValidator.extract_code_blocks()` with regex `r"```(?:python)?\s*(.*?)```"` and line-level heuristic fallback for unescaped code snippets. |
| **SEAM-04** | **LLM Judge String Substring False Negatives** | LLM Judge checked `if "client.search" in answer_text.lower()` for v2 callers. When agent surfaced unasked deprecation notice stating `"The v3.0 replacement is Client.search"`, judge flagged it as emitting v3 code to v2 caller! | **FIXED** | Modified `SdkEvalJudge` to extract and inspect the AST code block specifically for forbidden methods, rather than scanning prose deprecation warning text. |
| **SEAM-05** | **Stack Overflow Phrasing Dead API Bleed** | Stack Overflow answers carry valuable real-world phrasing keywords (e.g. "query without timeout") but include dead v1/v2 APIs (`Client.query`, `Stream.feed`) that v3 answers must never emit. | **FIXED** | Disallowed direct snippet emission from SO posts; partitioned SO dataset as query expansion vocabulary only, strictly filtered through caller's target version symbol table. |
| **SEAM-06** | **Mid-Function Code Snippet Splitting in Chunker** | Naive character/line splitters occasionally cut multi-line Python function calls across chunk boundaries (e.g., splitting `Client.search(` and `timeout=30)`). | **ACCEPTED** | Kept Week 4 structure-aware AST chunker. Rare edge cases where sample exceeds 1,200 tokens are accepted and documented in Known Weaknesses, as 99% of SDK snippets are under 40 lines. |
| **SEAM-07** | **In-IDE Multi-Tenant Socket Pool Concurrency** | Simulating 9,000 active concurrent WebSocket IDE connections over local MCP stdio transports causes thread exhaustion in test harness. | **ACCEPTED** | MCP stdio/in-memory bridge is maintained for single-tenant IDE agents. Enterprise multi-tenancy is deferred to horizontal proxy replicas in 10x scale plan. |
| **SEAM-08** | **Live Git Submodule Sync for `samples/` Repo** | Automating hourly GitHub webhook sync of client's live `samples/` repository into embedding vector store during eval runs. | **RAN-OUT-OF-TIME** | Packaged 200 tagged runnable samples directly into unified dataset (`data/code_samples_200.json`) rather than attempting live git network polling during local sandbox evaluation. Tracked for v3.1 production roadmap. |

---

## Seam Status Summary
- **Total Seams Identified:** 8
- **FIXED:** 5 (SEAM-01, SEAM-02, SEAM-03, SEAM-04, SEAM-05)
- **ACCEPTED:** 2 (SEAM-06, SEAM-07)
- **RAN-OUT-OF-TIME:** 1 (SEAM-08)
