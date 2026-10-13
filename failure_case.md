# Deliberate Failure Injection Report: Worker HTTP 500

## 1. Failure Scenario
- **Test Query:** `q3` (*"Migrate Stream.feed to v3: Check if the v3 OpenAPI spec upgrades to WebSockets (status 101); if so, subscribe with keep-alive heartbeat pings, otherwise use polling."*)
- **Target Worker:** `VersionDeprecationWorker` (Worker 1)
- **Injected Fault:** Forced HTTP 500 Internal Server Error (*"Deprecation registry service unavailable (connection timeout)"*).

---

## 2. Orchestrator Observed Behavior

### Did it retry the request?
**YES.** The Orchestrator caught the HTTP 500 status from Worker 1 and executed 1 immediate retry (`q3-HOP-1-RETRY`). When the retry also returned 500, it halted retry loops to avoid infinite runaway cost.

### Did it degrade gracefully into a partial answer?
**YES.** Rather than raising an unhandled exception or crashing the entire workflow, the Orchestrator transitioned to degraded execution mode. It passed the task forward to Worker 2 with an explicit disclaimer that deprecation validation was offline, allowing code generation to proceed against the active OpenAPI specification.

### Did it hallucinate or lie?
**NO.** The Orchestrator did NOT fabricate deprecation statuses or falsely claim that `Stream.feed` was active. It injected a prominent disclaimer into the final synthesized answer:
> *"[WARNING] DEGRADED ANSWER: Deprecation registry service returned HTTP 500. Generated v3 migration code based on active OpenAPI specification, but deprecation retirement could not be confirmed. Manual verification required."*

---

## 3. Delegation Trace During Failure

```
[Hop 1] orchestrator -> version_worker: Returns HTTP 500 (Connection Timeout)
[Hop 1-Retry] orchestrator -> version_worker: Retry returns HTTP 500 (Halt retry loop)
[Hop 2] orchestrator -> code_sample_worker: Dispatches code synthesis with degraded_mode=True
[Hop 3] orchestrator synthesis: Emits executable v3 code accompanied by deprecation disclaimer
```
