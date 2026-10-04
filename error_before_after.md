# Error Handling & Docstring-as-Prompt Rewrite: Before vs After

## 1. Tool Docstring Rewrite

### Before (Old Static Description)
```python
"Search prose documentation for keywords and concepts. Returns error if version directory is not found."
```

### After (Prompt-Engineered Recovery Docstring)
```python
"Search developer documentation, migration guides, and code examples for SDK usage patterns. "
"Call this tool whenever verifying endpoint changes or generating migration code. "
"If a queried version does not exist, inspect the returned recovery guidance for the latest "
"published active release (v3.2) and migration changelogs before generating code. "
"Do not hallucinate methods for unreleased versions."
```

---

## 2. Tool Raw Error Payload Comparison

### Before (Uninformative Opaque Error)
```json
{
  "content": [
    {
      "type": "text",
      "text": "Error 3: Documentation directory not found for version 'v4.0'"
    }
  ],
  "isError": true
}
```

### After (Actionable Recoverable Error)
```json
{
  "content": [
    {
      "type": "text",
      "text": "No documentation found for requested version 'v4.0'. The latest published active version is 'v3.2'. Deprecated methods and migration paths from v2 to v3 are documented under 'v3/migration' and 'v3/client_v3.txt'. Actionable Recovery: Please retry your query targeting version 'v3' or refer to 'v3.2' migration guides."
    }
  ],
  "isError": true
}
```

---

## 3. Execution Transcripts (Same Failing Call)

### Scenario
**Developer Prompt:** *"How do I migrate my Client.send call to v4.0 with updated backoff parameters?"*

---

### BEFORE TRANSCRIPT (Model Fails / Hallucinates)

```
[User]: How do I migrate my Client.send call to v4.0 with updated backoff parameters?

[Host Agent Reasoning]:
The user wants to migrate Client.send to version v4.0.
Invoking tool: search_docs(query="Client.send migration", version="v4.0")

[MCP Tool Call]:
--> tools/call: search_docs {"query": "Client.send migration", "version": "v4.0"}
<-- Tool Result (isError=true):
    "Error 3: Documentation directory not found for version 'v4.0'"

[Host Agent Reasoning]:
Tool returned 'Error 3'. The directory is missing. I will guess what v4.0 parameters might look like based on common industry conventions.

[Assistant Final Answer]:
I encountered an error looking up documentation (Error 3: Documentation directory not found).
However, in v4.0, Client.send likely introduces async backoff. You can configure it as:
```python
# Hallucinated unverified v4 code
client = ClientV4(endpoint="https://api.example.com")
response = client.send(
    payload={"query": "test"},
    exponential_backoff_max_ms=10000,
    async_retry=True
)
```
⚠️ **Failure Analysis:** The uninformative error caused the model to hallucinate non-existent API parameters (`ClientV4`, `async_retry`), shipping broken code to the user's codebase.

---

### AFTER TRANSCRIPT (Model Successfully Recovers)

```
[User]: How do I migrate my Client.send call to v4.0 with updated backoff parameters?

[Host Agent Reasoning]:
The user requests v4.0 migration guidance.
Invoking tool: search_docs(query="Client.send migration", version="v4.0")

[MCP Tool Call]:
--> tools/call: search_docs {"query": "Client.send migration", "version": "v4.0"}
<-- Tool Result (isError=true):
    "No documentation found for requested version 'v4.0'. The latest published active version is 'v3.2'. Deprecated methods and migration paths from v2 to v3 are documented under 'v3/migration' and 'v3/client_v3.txt'. Actionable Recovery: Please retry your query targeting version 'v3' or refer to 'v3.2' migration guides."

[Host Agent Reasoning]:
The tool explicitly informed me that v4.0 does not exist yet; the latest published active release is v3.2.
Following the tool's Actionable Recovery instruction:
Retrying search_docs targeting the active version 'v3'.

[MCP Tool Call (Recovery)]:
--> tools/call: search_docs {"query": "Client.send migration", "version": "v3"}
<-- Tool Result (isError=false):
    {
      "status": "success",
      "version": "v3",
      "count": 1,
      "results": [
        {
          "file": "client_v3.txt",
          "snippet": "Client.send() sends a structured payload with retry_backoff_ms=250 and timeout_s=30."
        }
      ]
    }

[Assistant Final Answer]:
Version 4.0 has not been released yet. According to the official SDK documentation, the latest published active release is **v3.2**.

For migrating `Client.send` to the latest active standard (v3), update your parameters as follows:
- `retry_backoff_ms`: Default reduced to `250` ms (from 500 ms in v2).
- `timeout_s`: Default configured to `30` seconds (from 60s in v2).

```python
client = Client(api_key="sk_live_v3_998877")
response = client.send(
    payload={"query": "analytics"},
    retry_backoff_ms=250,
    timeout_s=30
)
```
```
✅ **Success Analysis:** The model followed the tool's explicit recovery pathway, avoided hallucinating unreleased API signatures, and delivered grounded, verified v3 migration code.
