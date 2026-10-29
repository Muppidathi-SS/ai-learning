# The 10-Minute Technical Defense Demo Script — SDK Docs Answer Engine

**Domain:** Developer Documentation & SDK Migration Assistant (Variant E)  
**Time Limit:** Exactly 10:00 to the clock  
**Audience:** Technical Review Board, DevRel Leads, and AI Engineering Examiners  
**Core Motto:** *"A flawless demo is a red flag. Show the failure you found and how you know it's fixed."*

---

## Timing Overview
- **Part 1: The Real Run (Live Execution)** — 02:30 (Clock: 00:00 - 02:30)
- **Part 2: The Failures You Found** — 02:30 (Clock: 02:30 - 05:00)
- **Part 3: A Number That Moved** — 02:30 (Clock: 05:00 - 07:30)
- **Part 4: What's Next & 10x Scale** — 02:30 (Clock: 07:30 - 10:00)

---

## Part 1: The Real Run (Live Execution) — [00:00 - 02:30]

### Spoken Opening (00:00 - 00:30)
> *"Our client ships an SDK with 9,000 active developers. 40% are on v2.x; 60% are on v3.0. In v3, `client.query` was renamed to `client.search` and `timeout` became strictly mandatory. When a v2 customer gets a v3 snippet, it imports cleanly, passes code review, and fails in production. DevRel's most expensive tickets all begin: 'I copied this from your docs'. We don't care about answer rate — we care that emitted code actually runs. Let's run a real query on the clock."*

### Live Action 1: Query from a v2.4 Integrator (00:30 - 01:30)
Run in terminal:
```bash
python3 -c "from src.agent import IntegratedSdkDocsAgent; res = IntegratedSdkDocsAgent().answer_query('How do I query user records using Client.query in SDK v2.4?'); print(res.answer)"
```

**What to Point Out on Screen:**
1. **Version Resolution Before Retrieval:** Show the resolved version header: `Target SDK Version: v2.4 (Partition: v2)`. Point out that the retriever was pinned to `sdk_version == "v2"` before search began.
2. **Runnable v2 Code:** Show `client.query(payload=..., timeout=15)`. Point out that it parsed via Python AST and passed the v2 symbol-table check.
3. **Unasked Deprecation Surfaced:** Show the block:
   `> **Deprecation Notice (Removal in v3.0):** Client.query is scheduled for removal in v3.0. Replaced by Client.search... timeout becomes strictly mandatory.`
   Point out: *"Nobody asked about v3. We surfaced this unasked so their next release doesn't break."*
4. **Version-Tagged Citation:** Show `- [client_v2.md (SDK v2.x)](data/v2/client_v2.md#L1-L30)`. Point out: *"The citation names the SDK version explicitly. A link without an SDK version does not count."*

### Live Action 2: Breaking Method Query in v3.0 (01:30 - 02:30)
Run in terminal:
```bash
python3 -c "from src.agent import IntegratedSdkDocsAgent; res = IntegratedSdkDocsAgent().answer_query('Can I call Client.query in v3.0?'); print(res.answer)"
```

**What to Point Out on Screen:**
Show the verbatim response:
`🚨 Breaking Change in SDK v3.0: That method no longer exists in 3.0 — here is the migration:`
Point out: *"We do not helpfully invent a plausible signature. We state plainly that it no longer exists, and provide `client.search` with mandatory `timeout=30`."*

---

## Part 2: The Failures You Found — [02:30 - 05:00]

### Spoken Opening (02:30 - 03:00)
> *"A demo where nothing failed is a red flag. Here is the exact production failure we uncovered when we re-scored the Week 5 taxonomy across integrated traces."*

### Point 1: The Incident Trace (`tr_prod_20261016_8831f4`) (03:00 - 03:45)
- Open `taxonomy.md` or display the trace log.
- Explain: *"A v2.4 customer asked how to query records. Because the initial retrieval lacked version partitioning, it pulled an unpartitioned modern chunk and emitted `client.search(timeout=30)`. In v2.4, `Client.search` does not exist. The customer ran it and hit an `AttributeError`. That failure mode had an 18.2% frequency in our pre-fix taxonomy."*

### Point 2: The Mode Integration Created (`INTEGRATION_MCP_VERSION_DESYNC`) (03:45 - 04:15)
- Point to `taxonomy.md` Section 2:
- Explain: *"When we integrated the agent with our MCP server over JSON-RPC 2.0 on Tuesday, the agent passed string `'v2.4'`. The MCP server looked for directory `data/v2.4`, threw a not found error, and failed open to unpartitioned search! This mode didn't exist in the retriever alone or the MCP server alone. It was created strictly by integrating the parts. We fixed it with boundary normalization."*

### Point 3: The 2 Other Weaknesses Written on Wednesday Before Anyone Asked (04:15 - 05:00)
- Open `top3_weaknesses.md`:
  1. **Weakness 1 (AST Chunk Split):** Multi-line parameter lists cut across chunk boundaries on code examples exceeding 60 lines.
  2. **Weakness 2 (MCP Stdio Pipe Buffer):** Pipe contention at concurrency $>25$ threads causing 450ms latency spikes, requiring async SSE for multi-tenant deployment.

---

## Part 3: A Number That Moved — [05:00 - 07:30]

### Spoken Opening (05:00 - 05:30)
> *"Here is the number that moved. No adjectives — just sample size, before and after, judge agreement, and our explicit non-coverage."*

### The Metric & Sample Size (05:30 - 06:15)
- Open `eval_report.md`:
  - **Wrong-Version Code Emission Rate:**
    - Before: **18.8% (6/32)**
    - After: **0.0% (0/32)**
    - Sample size ($n$): **32 benchmark cases**
  - **AST Symbol-Table Pass Rate (Bonus Challenge):**
    - Moved from **68.8% $\rightarrow$ 100.0% (+31.2%)**.
    - *"We stopped judging code with an LLM and started executing the check: Python `ast.parse` and a symbol-table lookup against that version."*

### Validated Judge Agreement Rate (06:15 - 06:50)
- Point to Section 2 of `eval_report.md`:
  - **Judge Agreement Rate:** **`100.0%`** across $n=32$ cases (32/32 matches).
  - Clears the $\ge 85\%$ standard.
  - Confusion Matrix: 32 True Positives, 0 False Positives, 0 False Negatives.

### The Explicit Statement of Non-Coverage (06:50 - 07:30)
- Read verbatim from `eval_report.md`:
  > *"What our suite does NOT measure: The suite does NOT measure real-time network transport socket timeouts, client-side operating system TCP keepalive differences, or downstream API gateway 500 internal server errors in customer production clusters."*

---

## Part 4: What's Next & Scale — [07:30 - 10:00]

### Live Action 3: The Closed Failure-to-Test Loop (07:30 - 08:30)
Run in terminal:
```bash
MODE=RED python3 -m unittest tests/test_integrated_eval.py
```
- Show: `FAILED (failures=1)` on `test_01_closed_loop_incident_v2_query`.
- Point out: *"Here is the failing test case before fix: `Symbol Error in v2.x: Client.search() does not exist`."*

Run in terminal:
```bash
MODE=GREEN python3 -m unittest tests/test_integrated_eval.py
```
- Show: `Ran 32 tests ... OK` (100% pass, zero regressions).
- Point out: *"Here is the permanent test case guarding that failure in GREEN state."*

### Stage Cost Attribution & The 10x Scale Plan (08:30 - 09:30)
- Open `scale_10x.md`:
  - **Cost Per Question:** **`$0.001894 USD`** (Retrieval: $0.000350 / 18.5%, LLM Generation: $0.001544 / 81.5%, Symbol Validation: $0.000000 / 0.0%).
  - **What breaks first at 10x?**
    - Traffic: 750 QPM (615,000 TPM).
    - **Upstream LLM Token Rate Limit (250,000 TPM ceiling) breaks first at 305 QPM (4.06x baseline)**.
    - Not cost ($55k/mo is within budget). Not latency (p99 is 860ms). Rate limits break first.

### Defense Concluding Statement (09:30 - 10:00)
> *"Our system does not guess SDK versions, does not invent method signatures, and does not trust LLMs to say whether code compiles. It pins retrieval to the caller's version, parses code deterministically with AST, surfaces deprecations unasked, and maintains a single trace ID across every hop. The suite runs in one command and guards customer production. Thank you."*
