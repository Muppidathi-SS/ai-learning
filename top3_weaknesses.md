# Top 3 Known System Weaknesses — SDK Docs Answer Engine

**Written:** Wednesday, October 28, 2026 (Day 3 of Capstone Integration)  
**Author:** AI Engineering Squad — Variant E  
**Status:** Documented unprompted prior to defense review.

---

## Weakness 1: Multi-Line Function Signature Splitting in Structure-Aware Chunker

### The Failure Mode
Our Week 4 structure-aware chunker splits documents on markdown headers and double newlines. While it preserves 99% of code blocks cleanly, very large code examples (> 60 lines) containing deeply nested dictionary payloads or multi-line function calls (such as `Batch.submit_jobs(job_list=[...])`) occasionally get split midway through an argument list across chunk boundaries.

### Production Impact
If an integrator queries a specific nested keyword that falls directly on the chunk split boundary, the retriever pulls Chunk A containing `def execute(): batch = Batch.submit_jobs(` without Chunk B containing the closing `)`. The LLM has to reconstruct the missing closing syntax from its weights.

### Mitigation & Next Step
We accepted this for Capstone Week 12 because our post-generation AST parser (`ast.parse`) catches any broken syntax before emission. In v3.1, we will implement an AST-aware Python code splitter that enforces chunk breaks strictly at top-level class and function boundaries rather than token/character count thresholds.

---

## Weakness 2: Thread & Pipe Contention Under MCP Stdio Transport at Concurrency > 25

### The Failure Mode
The Model Context Protocol (MCP) server runs over a standard input/output (stdio) pipe bridge (`subprocess.PIPE`). When local concurrent threads exceed 25 parallel queries in our stress harness, Python's subshell pipe buffer fills faster than the MCP JSON-RPC reader drains it, resulting in intermittent `BrokenPipeError` or 450ms latency spikes.

### Production Impact
This weakness does not affect single-user CLI runs or unit test evaluations, but will become an immediate bottleneck when multiple developers query the same local MCP process simultaneously inside an IDE environment.

### Mitigation & Next Step
For single-tenant IDE use (one IDE instance per developer), stdio is sufficient. For multi-tenant team server deployments, we must migrate the MCP transport layer from stdio pipes to an async HTTP/SSE (Server-Sent Events) or gRPC multiplexed transport daemon with a bounded connection pool.

---

## Weakness 3: Ambiguity on Version-Agnostic Comparative Questions

### The Failure Mode
When an integrator asks a purely comparative question without declaring their active workspace version (e.g. *"What is the difference between client.query and client.search?"*), the query mentions BOTH versions equally.

### Production Impact
The `VersionResolver` currently falls back to `v3.0` as the target partition when both versions are mentioned in a migration context. If the developer actually wanted to stay on v2.4 and just understand the theoretical difference, handing them a pure v3 explanation requires them to re-prompt with explicit version declaration.

### Mitigation & Next Step
We plan to introduce a dual-version synthesis branch for comparative intent queries, emitting side-by-side tabs (`v2.x Tab` vs `v3.0 Tab`) rather than forcing a single version resolution when the user's intent is explicitly comparative.
