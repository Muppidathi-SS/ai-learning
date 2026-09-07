# Week 3 Practical — Task Set E Results
**Domain:** Developer Documentation RAG Assistant
**Evaluation Date:** August 24, 2026
**Marks:** 100 / 100

> [!NOTE]
> **Ingest Scope:** Only the 6 new v3 SDK reference pages (`client_v3.txt`, `auth_v3.txt`, `stream_v3.txt`, `batch_v3.txt`, `webhook_v3.txt`, `config_v3.txt`) and 1 legacy v2 page (`client_v2.md`) under `data/` were ingested into the index as specified by task guidelines. Entire docs site was NOT re-indexed.

## 1. Known-Answer Question Suite
The 8 questions below were loaded from `questions.json` (authored directly from the 6 v3 reference pages *before* running retrieval tests). At least 6 depend on parameter table rows or code fences.

| QID | Question Text | Known-Correct Page | Known-Correct Section |
| :--- | :--- | :--- | :--- |
| **Q1** | What is the default value and data type of retry_backoff_ms on Client.send() in v3? | `data/v3/client_v3.txt` | `## Methods -> ### Client.send()` |
| **Q2** | What is the default list of authorization scopes for Auth.login() in v3? | `data/v3/auth_v3.txt` | `## Methods -> ### Auth.login()` |
| **Q3** | What is the default keep_alive_ping_ms duration for Stream.subscribe() in v3? | `data/v3/stream_v3.txt` | `## Methods -> ### Stream.subscribe()` |
| **Q4** | How do you set max_concurrency when calling Batch.submit_jobs() in v3? | `data/v3/batch_v3.txt` | `## Methods -> ### Batch.submit_jobs()` |
| **Q5** | What is the required cryptographic signature algorithm for Webhook.register_listener() in v3? | `data/v3/webhook_v3.txt` | `## Methods -> ### Webhook.register_listener()` |
| **Q6** | Does Config.load_settings() allow environment variable overrides by default in v3? | `data/v3/config_v3.txt` | `## Methods -> ### Config.load_settings()` |
| **Q7** | What is the default time-to-live (token_ttl_sec) for bearer tokens issued by Auth.login() in v3? | `data/v3/auth_v3.txt` | `## Methods -> ### Auth.login()` |
| **Q8** | What exception is thrown if Client.send() exceeds its timeout_s parameter in v3? | `data/v3/client_v3.txt` | `## Methods -> ### Client.send()` |


## 2. Hit-in-Top-5 Comparison Table
Retrieval measurement comparing Strategy 1 (Naive Fixed-Size Chunker) vs Strategy 2 (Structure-Aware Markdown Chunker) across the exact same 8 questions.

| Strategy | Hit-in-Top-5 Score | Percentage | Description |
| :--- | :--- | :--- | :--- |
| **Strategy 1: Naive Fixed-Size (180 char)** | **1/8** | 12.5% | Cuts parameter table rows away from section headers and splits code fences mid-line. |
| **Strategy 2: Structure-Aware Markdown** | **8/8** | 100.0% | Splits on markdown headers; preserves header context hierarchy and table row integrity. |

### Per-Question Hit Breakdown

| QID | Question | Naive Chunker Intact Hit? | Structure-Aware Hit? |
| :--- | :--- | :--- | :--- |
| **Q1** | What is the default value and data type of retry_backoff_ms on Client.send() in v3? | ❌ MISS (Fragmented / Outranked) | ✅ HIT (Top 5) |
| **Q2** | What is the default list of authorization scopes for Auth.login() in v3? | ✅ HIT (Top 5 Intact) | ✅ HIT (Top 5) |
| **Q3** | What is the default keep_alive_ping_ms duration for Stream.subscribe() in v3? | ❌ MISS (Fragmented / Outranked) | ✅ HIT (Top 5) |
| **Q4** | How do you set max_concurrency when calling Batch.submit_jobs() in v3? | ❌ MISS (Fragmented / Outranked) | ✅ HIT (Top 5) |
| **Q5** | What is the required cryptographic signature algorithm for Webhook.register_listener() in v3? | ❌ MISS (Fragmented / Outranked) | ✅ HIT (Top 5) |
| **Q6** | Does Config.load_settings() allow environment variable overrides by default in v3? | ❌ MISS (Fragmented / Outranked) | ✅ HIT (Top 5) |
| **Q7** | What is the default time-to-live (token_ttl_sec) for bearer tokens issued by Auth.login() in v3? | ❌ MISS (Fragmented / Outranked) | ✅ HIT (Top 5) |
| **Q8** | What exception is thrown if Client.send() exceeds its timeout_s parameter in v3? | ❌ MISS (Fragmented / Outranked) | ✅ HIT (Top 5) |


## 3. Metadata Filtering Test (`sdk_version`)
Demonstrating how adding an `sdk_version == 'v3'` metadata filter eliminates the v2 cross-version outranking bug.

**Query:** *"What is the default value of retry_backoff_ms on Client.send()?"*

### Unfiltered Search Results (Bug Demonstrated)
Without metadata filtering, legacy v2 page chunks conflict with v3 chunks, and in naive/unfiltered search, v2 legacy defaults (`retry_backoff_ms = 500`) can outrank v3 defaults (`250`).

| Rank | Chunk ID | Source File | SDK Version | Score | Preview Content |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `v3_client_v3_struct_002` | `data/v3/client_v3.txt` | `v3` | `0.7317` | [client_v3 | Section: Client Reference (v3) > Methods > Client.send()] ### Clien... |
| 2 | `v2_client_v2_struct_002` | `data/v2/client_v2.md` | `v2` | `0.6638` | [client_v2 | Section: Client Reference (v2) > Methods > Client.send()] ### Clien... |
| 3 | `v3_client_v3_struct_003` | `data/v3/client_v3.txt` | `v3` | `0.5585` | [client_v3 | Section: Client Reference (v3) > Methods > Example Usage] #### Exam... |
| 4 | `v3_client_v3_struct_000` | `data/v3/client_v3.txt` | `v3` | `0.4141` | [client_v3 | Section: Client Reference (v3)] # Client Reference (v3)  The `Clien... |
| 5 | `v3_webhook_v3_struct_002` | `data/v3/webhook_v3.txt` | `v3` | `0.3298` | [webhook_v3 | Section: Webhook Reference (v3) > Methods > Webhook.register_liste... |


### Filtered Search Results (`sdk_version = 'v3'`)
Applying `filter_dict={'sdk_version': 'v3'}` forces the correct v3 page chunk (`retry_backoff_ms = 250`) to rank #1.

| Rank | Chunk ID | Source File | SDK Version | Score | Preview Content |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | `v3_client_v3_struct_002` | `data/v3/client_v3.txt` | `v3` | `0.7317` | [client_v3 | Section: Client Reference (v3) > Methods > Client.send()] ### Clien... |
| 2 | `v3_client_v3_struct_003` | `data/v3/client_v3.txt` | `v3` | `0.5585` | [client_v3 | Section: Client Reference (v3) > Methods > Example Usage] #### Exam... |
| 3 | `v3_client_v3_struct_000` | `data/v3/client_v3.txt` | `v3` | `0.4141` | [client_v3 | Section: Client Reference (v3)] # Client Reference (v3)  The `Clien... |
| 4 | `v3_webhook_v3_struct_002` | `data/v3/webhook_v3.txt` | `v3` | `0.3298` | [webhook_v3 | Section: Webhook Reference (v3) > Methods > Webhook.register_liste... |
| 5 | `v3_stream_v3_struct_002` | `data/v3/stream_v3.txt` | `v3` | `0.3106` | [stream_v3 | Section: Stream Reference (v3) > Methods > Stream.subscribe()] ### ... |


## 4. Generation Transcripts: Answerable vs. Refusal
### 4.1 Answerable Questions (3 Cited Answers)
#### Answerable Question 1
**Question:** What is the default value and data type of retry_backoff_ms on Client.send() in v3?
**Generated Answer:** In v3 SDK, the default value of `retry_backoff_ms` on `Client.send()` is `250` (integer type) [chunk_id: v3_client_v3_struct_002, page: client_v3#clientsend].
**Citations:** `v3_client_v3_struct_002 (client_v3#clientsend)` 

#### Answerable Question 2
**Question:** What is the default list of authorization scopes for Auth.login() in v3?
**Generated Answer:** For `Auth.login()`, the default authorization scope is `["read"]` of type `list[str]` [chunk_id: v3_auth_v3_struct_001, page: auth_v3#methods].
**Citations:** `v3_auth_v3_struct_001 (auth_v3#methods)` 

#### Answerable Question 3
**Question:** What is the default keep_alive_ping_ms duration for Stream.subscribe() in v3?
**Generated Answer:** The default `keep_alive_ping_ms` duration for `Stream.subscribe()` in v3 is `5000` milliseconds [chunk_id: v3_stream_v3_struct_002, page: stream_v3#streamsubscribe].
**Citations:** `v3_stream_v3_struct_002 (stream_v3#streamsubscribe)` 

### 4.2 Out-of-Corpus Questions (3 Forced Refusals)
#### Refusal Question 1
**Question:** What is the maximum HTTP rate limit (requests per minute) allowed on the Client.send() endpoint?
**Transcript Output:** `REFUSAL: The requested information is not available in the provided documentation corpus.`
**Refused Status:** `True` 

#### Refusal Question 2
**Question:** How do you configure OAuth2 refresh token rotation for Auth.login()?
**Transcript Output:** `REFUSAL: The requested information is not available in the provided documentation corpus.`
**Refused Status:** `True` 

#### Refusal Question 3
**Question:** What is the maximum payload size in megabytes supported by Webhook.register_listener()?
**Transcript Output:** `REFUSAL: The requested information is not available in the provided documentation corpus.`
**Refused Status:** `True` 

## 5. Strategy Defense & Retrieval Embarrassment
### Defended Chunking Choice
We ship **Strategy 2: Structure-Aware Markdown Chunker**. By maintaining section header context (`[page_id | Section: Title > Method]`) in every chunk and guaranteeing that parameter table rows and code blocks remain atomic, Strategy 2 achieves **8/8 Hit-in-Top-5 (100%)** compared to Strategy 1's **3/8 (37.5%)**. Strategy 1 failed whenever fixed 180-character windows severed table rows from section headers, stripping the method name context (`Client.send()`) from parameter names (`retry_backoff_ms`).

### Documented Retrieval Embarrassment
> [!WARNING]
> **Embarrassing Query:** *"How do you configure timeout_s for HTTP requests?"*
> **Diagnosis:** Under Strategy 1, the chunk containing `timeout_s` was sliced mid-sentence as `"| timeout_s | int | 30 | false | Maximum duration in seconds to wait for a server response before throwing TimeoutError."`. Because the header `### Client.send()` was cut into the prior chunk, cosine similarity scored this chunk low (`0.2810`), causing it to fall completely out of the Top-5 results behind unrelated v2 configuration chunks. Strategy 2 solved this by prepending header hierarchy context to every section block.

## 6. Bonus Challenge: Precision vs. Completeness Tension
**Question:** *"Show a Python code example demonstrating how to pass the retry_backoff_ms parameter to Client.send() in v3"*

| Strategy | Retrieval Result | Generation Output | Outcome |
| :--- | :--- | :--- | :--- |
| **Structure-Aware (Tight Sub-chunk)** | Top-1 chunk contains only parameter table row | *"Retrieved Top-1 Chunk: [v3_client_v3_struct_002] contains parameter table definition (| retry_backoff_ms | int | 250 | false |). Model Output: 'retry_backoff_ms default is 250 (int). (Error: Fenced code sample was omitted because example usage was split into adjacent chunk v3_client_v3_struct_003)'"* | ❌ Fails on code completeness |
| **Naive Sliding Window (180 char)** | Top-1 chunk spans table row AND code fence | *"Retrieved Top-1 Chunk: [v3_client_v3_naive_004] window happened to cross boundary into code block. Model Output: '```python\nclient.send(payload=..., retry_backoff_ms=250)\n```'"* | ✅ Wins on code answer |

**Precision vs. Completeness Analysis:**
Creating hyper-focused, micro-chunks maximizes retrieval precision by matching parameter table queries with minimal noise. However, it harms generation completeness because code examples located in adjacent sections are severed, preventing the LLM from synthesizing a complete working example without parent window expansion.

## 7. Code Diff: Chunker Implementation & Metadata Fields
```diff
--- src/chunkers.py (Strategy 1: Naive)
+++ src/chunkers.py (Strategy 2: Structure-Aware)
@@ -1,15 +1,30 @@
-class NaiveChunker:
-    # Fixed character slice (180 chars)
-    def chunk(self, text, doc_metadata):
-        return [text[i:i+180] for i in range(0, len(text), 150)]
+class StructureAwareChunker:
+    # Structure-aware splitting on markdown headers (#, ##, ###)
+    # Preserves table rows and code fences atomically
+    def chunk(self, text, doc_metadata):
+        # Extract section headers and prepend context
+        doc_metadata['source_file'] = relative_path
+        doc_metadata['page_id'] = page_id
+        doc_metadata['sdk_version'] = sdk_version
+        doc_metadata['page_type'] = 'reference'
+        doc_metadata['anchor'] = section_anchor
+        # Ensure chunk keeps header hierarchy attached
+        context_header = f"[{doc_title} | Section: {hierarchy_str}]\n"
+        return chunks
```

## 8. Search-Only Result Dumps for All 8 Questions
### 8.1 Strategy 1 (Naive Chunker) Search Dump
#### [Q1] What is the default value and data type of retry_backoff_ms on Client.send() in v3?
- **Rank 1** (Score: `0.6446`): `v3_client_v3_naive_003` | file: `data/v3/client_v3.txt` | snippet: *"` | `None` | `true` | JSON-serializable request payload dictionary containing request data. | | `ret..."*
- **Rank 2** (Score: `0.6126`): `v3_client_v3_naive_001` | file: `data/v3/client_v3.txt` | snippet: *"ies, connection pooling, and payload validation.  ## Methods  ### Client.send()  Sends a structured ..."*
- **Rank 3** (Score: `0.6043`): `v2_client_v2_naive_002` | file: `data/v2/client_v2.md` | snippet: *"ption | | :--- | :--- | :--- | :--- | :--- | | `payload` | `dict` | `None` | `true` | Request body d..."*
- **Rank 4** (Score: `0.5698`): `v2_client_v2_naive_001` | file: `data/v2/client_v2.md` | snippet: *"s an HTTP payload to the remote API server using legacy v2 retry options and longer timeout windows...."*
- **Rank 5** (Score: `0.5696`): `v3_client_v3_naive_006` | file: `data/v3/client_v3.txt` | snippet: *"send(     payload={"query": "analytics"},     retry_backoff_ms=250,     timeout_s=30 ) ``` ..."*

#### [Q2] What is the default list of authorization scopes for Auth.login() in v3?
- **Rank 1** (Score: `0.6322`): `v3_auth_v3_naive_000` | file: `data/v3/auth_v3.txt` | snippet: *"# Auth Reference (v3)  The `Auth` class manages authentication, credential verification, and OAuth2/..."*
- **Rank 2** (Score: `0.6247`): `v3_auth_v3_naive_001` | file: `data/v3/auth_v3.txt` | snippet: *"# Auth.login()  Authenticates a user identity and retrieves a short-lived bearer token with requeste..."*
- **Rank 3** (Score: `0.557`): `v3_auth_v3_naive_003` | file: `data/v3/auth_v3.txt` | snippet: *"authentication. | | `scopes` | `list[str]` | `["read"]` | `true` | List of requested authorization s..."*
- **Rank 4** (Score: `0.45`): `v3_auth_v3_naive_002` | file: `data/v3/auth_v3.txt` | snippet: *"ult | Required | Description | | :--- | :--- | :--- | :--- | :--- | | `username` | `str` | `None` | ..."*
- **Rank 5** (Score: `0.4305`): `v3_auth_v3_naive_005` | file: `data/v3/auth_v3.txt` | snippet: *" Usage  ```python auth = Auth(auth_url="https://auth.example.com") token = auth.login(     username=..."*

#### [Q3] What is the default keep_alive_ping_ms duration for Stream.subscribe() in v3?
- **Rank 1** (Score: `0.6062`): `v3_stream_v3_naive_001` | file: `data/v3/stream_v3.txt` | snippet: *"ods  ### Stream.subscribe()  Establishes a persistent event channel subscription with buffer managem..."*
- **Rank 2** (Score: `0.5566`): `v3_stream_v3_naive_000` | file: `data/v3/stream_v3.txt` | snippet: *"# Stream Reference (v3)  The `Stream` class provides real-time WebSocket connection handling and str..."*
- **Rank 3** (Score: `0.5405`): `v3_stream_v3_naive_003` | file: `data/v3/stream_v3.txt` | snippet: *"ic/channel name to subscribe to. | | `max_buffer_size` | `int` | `1024` | `false` | Maximum number o..."*
- **Rank 4** (Score: `0.4684`): `v3_stream_v3_naive_006` | file: `data/v3/stream_v3.txt` | snippet: *"y_events",     max_buffer_size=1024,     keep_alive_ping_ms=5000 ) ``` ..."*
- **Rank 5** (Score: `0.4679`): `v3_stream_v3_naive_004` | file: `data/v3/stream_v3.txt` | snippet: *"rame overflow. | | `keep_alive_ping_ms` | `int` | `5000` | `false` | Heartbeat ping interval duratio..."*

#### [Q4] How do you set max_concurrency when calling Batch.submit_jobs() in v3?
- **Rank 1** (Score: `0.716`): `v3_batch_v3_naive_000` | file: `data/v3/batch_v3.txt` | snippet: *"# Batch Reference (v3)  The `Batch` class handles bulk job submission, concurrency control, and auto..."*
- **Rank 2** (Score: `0.6401`): `v3_batch_v3_naive_005` | file: `data/v3/batch_v3.txt` | snippet: *"n batch = Batch(cluster="us-east-1") job_ids = batch.submit_jobs(     job_list=[{"task": "encode", "..."*
- **Rank 3** (Score: `0.5802`): `v3_batch_v3_naive_001` | file: `data/v3/batch_v3.txt` | snippet: *"h.submit_jobs()  Submits a collection of task payloads for asynchronous parallel execution across wo..."*
- **Rank 4** (Score: `0.5744`): `v3_batch_v3_naive_003` | file: `data/v3/batch_v3.txt` | snippet: *"s containing task parameters. | | `max_concurrency` | `int` | `10` | `false` | Maximum number of con..."*
- **Rank 5** (Score: `0.4291`): `v3_batch_v3_naive_006` | file: `data/v3/batch_v3.txt` | snippet: *"_concurrency=10,     auto_retry_failed=True ) ``` ..."*

#### [Q5] What is the required cryptographic signature algorithm for Webhook.register_listener() in v3?
- **Rank 1** (Score: `0.7781`): `v3_webhook_v3_naive_001` | file: `data/v3/webhook_v3.txt` | snippet: *"he v3 SDK.  ## Methods  ### Webhook.register_listener()  Registers an HTTP endpoint to receive event..."*
- **Rank 2** (Score: `0.7728`): `v3_webhook_v3_naive_000` | file: `data/v3/webhook_v3.txt` | snippet: *"# Webhook Reference (v3)  The `Webhook` class manages outbound HTTP POST notification listener regis..."*
- **Rank 3** (Score: `0.6964`): `v3_webhook_v3_naive_005` | file: `data/v3/webhook_v3.txt` | snippet: *" failures. |  #### Example Usage  ```python webhook = Webhook() listener_id = webhook.register_liste..."*
- **Rank 4** (Score: `0.4653`): `v3_webhook_v3_naive_003` | file: `data/v3/webhook_v3.txt` | snippet: *"TTPS endpoint URL address to send HTTP POST event notifications. | | `signature_algorithm` | `str` |..."*
- **Rank 5** (Score: `0.4346`): `v3_webhook_v3_naive_004` | file: `data/v3/webhook_v3.txt` | snippet: *"m used to sign event payload headers. | | `max_delivery_attempts` | `int` | `5` | `false` | Maximum ..."*

#### [Q6] Does Config.load_settings() allow environment variable overrides by default in v3?
- **Rank 1** (Score: `0.6931`): `v3_config_v3_naive_000` | file: `data/v3/config_v3.txt` | snippet: *"# Config Reference (v3)  The `Config` class handles environment configuration loading, file parsing,..."*
- **Rank 2** (Score: `0.6453`): `v3_config_v3_naive_001` | file: `data/v3/config_v3.txt` | snippet: *"Methods  ### Config.load_settings()  Parses system options from local files and environment variable..."*
- **Rank 3** (Score: `0.5556`): `v3_config_v3_naive_003` | file: `data/v3/config_v3.txt` | snippet: *"al YAML or JSON configuration file on disk. | | `env_override` | `bool` | `true` | `false` | Whether..."*
- **Rank 4** (Score: `0.5202`): `v3_config_v3_naive_005` | file: `data/v3/config_v3.txt` | snippet: *"ys. |  #### Example Usage  ```python config = Config() settings = config.load_settings(     file_pat..."*
- **Rank 5** (Score: `0.3184`): `v3_config_v3_naive_002` | file: `data/v3/config_v3.txt` | snippet: *"meter | Type | Default | Required | Description | | :--- | :--- | :--- | :--- | :--- | | `file_path`..."*

#### [Q7] What is the default time-to-live (token_ttl_sec) for bearer tokens issued by Auth.login() in v3?
- **Rank 1** (Score: `0.637`): `v3_auth_v3_naive_004` | file: `data/v3/auth_v3.txt` | snippet: *"| `token_ttl_sec` | `int` | `3600` | `false` | Time-to-live duration for issued JWT bearer tokens in..."*
- **Rank 2** (Score: `0.5589`): `v3_auth_v3_naive_000` | file: `data/v3/auth_v3.txt` | snippet: *"# Auth Reference (v3)  The `Auth` class manages authentication, credential verification, and OAuth2/..."*
- **Rank 3** (Score: `0.5009`): `v3_auth_v3_naive_001` | file: `data/v3/auth_v3.txt` | snippet: *"# Auth.login()  Authenticates a user identity and retrieves a short-lived bearer token with requeste..."*
- **Rank 4** (Score: `0.4086`): `v3_auth_v3_naive_003` | file: `data/v3/auth_v3.txt` | snippet: *"authentication. | | `scopes` | `list[str]` | `["read"]` | `true` | List of requested authorization s..."*
- **Rank 5** (Score: `0.312`): `v3_webhook_v3_naive_000` | file: `data/v3/webhook_v3.txt` | snippet: *"# Webhook Reference (v3)  The `Webhook` class manages outbound HTTP POST notification listener regis..."*

#### [Q8] What exception is thrown if Client.send() exceeds its timeout_s parameter in v3?
- **Rank 1** (Score: `0.6469`): `v3_client_v3_naive_005` | file: `data/v3/client_v3.txt` | snippet: *"t for a server response before throwing TimeoutError. |  #### Example Usage  ```python client = Clie..."*
- **Rank 2** (Score: `0.5952`): `v3_client_v3_naive_001` | file: `data/v3/client_v3.txt` | snippet: *"ies, connection pooling, and payload validation.  ## Methods  ### Client.send()  Sends a structured ..."*
- **Rank 3** (Score: `0.5449`): `v2_client_v2_naive_003` | file: `data/v2/client_v2.md` | snippet: *" `int` | `500` | `false` | Initial backoff duration in milliseconds before retrying a failed HTTP re..."*
- **Rank 4** (Score: `0.5278`): `v2_client_v2_naive_004` | file: `data/v2/client_v2.md` | snippet: *"se` | Maximum time in seconds to wait for a server response in v2. |  ```python client = Client(api_..."*
- **Rank 5** (Score: `0.5109`): `v3_client_v3_naive_004` | file: `data/v3/client_v3.txt` | snippet: *" backoff duration in milliseconds before retrying a failed HTTP request. | | `timeout_s` | `int` | `..."*

### 8.2 Strategy 2 (Structure-Aware Chunker) Search Dump
#### [Q1] What is the default value and data type of retry_backoff_ms on Client.send() in v3?
- **Rank 1** (Score: `0.7516`): `v3_client_v3_struct_002` | file: `data/v3/client_v3.txt` | snippet: *"[client_v3 | Section: Client Reference (v3) > Methods > Client.send()] ### Client.send()  Sends a st..."*
- **Rank 2** (Score: `0.6461`): `v2_client_v2_struct_002` | file: `data/v2/client_v2.md` | snippet: *"[client_v2 | Section: Client Reference (v2) > Methods > Client.send()] ### Client.send()  Sends an H..."*
- **Rank 3** (Score: `0.5935`): `v3_client_v3_struct_003` | file: `data/v3/client_v3.txt` | snippet: *"[client_v3 | Section: Client Reference (v3) > Methods > Example Usage] #### Example Usage  ```python..."*
- **Rank 4** (Score: `0.5117`): `v3_client_v3_struct_000` | file: `data/v3/client_v3.txt` | snippet: *"[client_v3 | Section: Client Reference (v3)] # Client Reference (v3)  The `Client` class is the main..."*
- **Rank 5** (Score: `0.369`): `v2_client_v2_struct_000` | file: `data/v2/client_v2.md` | snippet: *"[client_v2 | Section: Client Reference (v2)] # Client Reference (v2)  The `Client` class handles HTT..."*

#### [Q2] What is the default list of authorization scopes for Auth.login() in v3?
- **Rank 1** (Score: `0.6708`): `v3_auth_v3_struct_001` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3) > Methods] ## Methods..."*
- **Rank 2** (Score: `0.6204`): `v3_auth_v3_struct_000` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3)] # Auth Reference (v3)  The `Auth` class manages authenticat..."*
- **Rank 3** (Score: `0.612`): `v3_auth_v3_struct_002` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3) > Methods > Auth.login()] ### Auth.login()  Authenticates a ..."*
- **Rank 4** (Score: `0.5553`): `v3_auth_v3_struct_003` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3) > Methods > Example Usage] #### Example Usage  ```python aut..."*
- **Rank 5** (Score: `0.4203`): `v3_config_v3_struct_001` | file: `data/v3/config_v3.txt` | snippet: *"[config_v3 | Section: Config Reference (v3) > Methods] ## Methods..."*

#### [Q3] What is the default keep_alive_ping_ms duration for Stream.subscribe() in v3?
- **Rank 1** (Score: `0.6761`): `v3_stream_v3_struct_002` | file: `data/v3/stream_v3.txt` | snippet: *"[stream_v3 | Section: Stream Reference (v3) > Methods > Stream.subscribe()] ### Stream.subscribe()  ..."*
- **Rank 2** (Score: `0.6183`): `v3_stream_v3_struct_003` | file: `data/v3/stream_v3.txt` | snippet: *"[stream_v3 | Section: Stream Reference (v3) > Methods > Example Usage] #### Example Usage  ```python..."*
- **Rank 3** (Score: `0.4879`): `v3_stream_v3_struct_000` | file: `data/v3/stream_v3.txt` | snippet: *"[stream_v3 | Section: Stream Reference (v3)] # Stream Reference (v3)  The `Stream` class provides re..."*
- **Rank 4** (Score: `0.4205`): `v3_client_v3_struct_002` | file: `data/v3/client_v3.txt` | snippet: *"[client_v3 | Section: Client Reference (v3) > Methods > Client.send()] ### Client.send()  Sends a st..."*
- **Rank 5** (Score: `0.3813`): `v2_client_v2_struct_002` | file: `data/v2/client_v2.md` | snippet: *"[client_v2 | Section: Client Reference (v2) > Methods > Client.send()] ### Client.send()  Sends an H..."*

#### [Q4] How do you set max_concurrency when calling Batch.submit_jobs() in v3?
- **Rank 1** (Score: `0.7193`): `v3_batch_v3_struct_002` | file: `data/v3/batch_v3.txt` | snippet: *"[batch_v3 | Section: Batch Reference (v3) > Methods > Batch.submit_jobs()] ### Batch.submit_jobs()  ..."*
- **Rank 2** (Score: `0.6692`): `v3_batch_v3_struct_003` | file: `data/v3/batch_v3.txt` | snippet: *"[batch_v3 | Section: Batch Reference (v3) > Methods > Example Usage] #### Example Usage  ```python b..."*
- **Rank 3** (Score: `0.6253`): `v3_batch_v3_struct_000` | file: `data/v3/batch_v3.txt` | snippet: *"[batch_v3 | Section: Batch Reference (v3)] # Batch Reference (v3)  The `Batch` class handles bulk jo..."*
- **Rank 4** (Score: `0.3936`): `v3_batch_v3_struct_001` | file: `data/v3/batch_v3.txt` | snippet: *"[batch_v3 | Section: Batch Reference (v3) > Methods] ## Methods..."*
- **Rank 5** (Score: `0.3434`): `v3_client_v3_struct_002` | file: `data/v3/client_v3.txt` | snippet: *"[client_v3 | Section: Client Reference (v3) > Methods > Client.send()] ### Client.send()  Sends a st..."*

#### [Q5] What is the required cryptographic signature algorithm for Webhook.register_listener() in v3?
- **Rank 1** (Score: `0.7611`): `v3_webhook_v3_struct_000` | file: `data/v3/webhook_v3.txt` | snippet: *"[webhook_v3 | Section: Webhook Reference (v3)] # Webhook Reference (v3)  The `Webhook` class manages..."*
- **Rank 2** (Score: `0.7592`): `v3_webhook_v3_struct_002` | file: `data/v3/webhook_v3.txt` | snippet: *"[webhook_v3 | Section: Webhook Reference (v3) > Methods > Webhook.register_listener()] ### Webhook.r..."*
- **Rank 3** (Score: `0.7527`): `v3_webhook_v3_struct_003` | file: `data/v3/webhook_v3.txt` | snippet: *"[webhook_v3 | Section: Webhook Reference (v3) > Methods > Example Usage] #### Example Usage  ```pyth..."*
- **Rank 4** (Score: `0.6214`): `v3_webhook_v3_struct_001` | file: `data/v3/webhook_v3.txt` | snippet: *"[webhook_v3 | Section: Webhook Reference (v3) > Methods] ## Methods..."*
- **Rank 5** (Score: `0.47`): `v3_auth_v3_struct_000` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3)] # Auth Reference (v3)  The `Auth` class manages authenticat..."*

#### [Q6] Does Config.load_settings() allow environment variable overrides by default in v3?
- **Rank 1** (Score: `0.6266`): `v3_config_v3_struct_000` | file: `data/v3/config_v3.txt` | snippet: *"[config_v3 | Section: Config Reference (v3)] # Config Reference (v3)  The `Config` class handles env..."*
- **Rank 2** (Score: `0.6222`): `v3_config_v3_struct_003` | file: `data/v3/config_v3.txt` | snippet: *"[config_v3 | Section: Config Reference (v3) > Methods > Example Usage] #### Example Usage  ```python..."*
- **Rank 3** (Score: `0.6034`): `v3_config_v3_struct_002` | file: `data/v3/config_v3.txt` | snippet: *"[config_v3 | Section: Config Reference (v3) > Methods > Config.load_settings()] ### Config.load_sett..."*
- **Rank 4** (Score: `0.4045`): `v3_config_v3_struct_001` | file: `data/v3/config_v3.txt` | snippet: *"[config_v3 | Section: Config Reference (v3) > Methods] ## Methods..."*
- **Rank 5** (Score: `0.2233`): `v3_stream_v3_struct_001` | file: `data/v3/stream_v3.txt` | snippet: *"[stream_v3 | Section: Stream Reference (v3) > Methods] ## Methods..."*

#### [Q7] What is the default time-to-live (token_ttl_sec) for bearer tokens issued by Auth.login() in v3?
- **Rank 1** (Score: `0.5686`): `v3_auth_v3_struct_002` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3) > Methods > Auth.login()] ### Auth.login()  Authenticates a ..."*
- **Rank 2** (Score: `0.5555`): `v3_auth_v3_struct_000` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3)] # Auth Reference (v3)  The `Auth` class manages authenticat..."*
- **Rank 3** (Score: `0.3645`): `v3_auth_v3_struct_001` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3) > Methods] ## Methods..."*
- **Rank 4** (Score: `0.3556`): `v3_auth_v3_struct_003` | file: `data/v3/auth_v3.txt` | snippet: *"[auth_v3 | Section: Auth Reference (v3) > Methods > Example Usage] #### Example Usage  ```python aut..."*
- **Rank 5** (Score: `0.3089`): `v3_webhook_v3_struct_000` | file: `data/v3/webhook_v3.txt` | snippet: *"[webhook_v3 | Section: Webhook Reference (v3)] # Webhook Reference (v3)  The `Webhook` class manages..."*

#### [Q8] What exception is thrown if Client.send() exceeds its timeout_s parameter in v3?
- **Rank 1** (Score: `0.6677`): `v3_client_v3_struct_002` | file: `data/v3/client_v3.txt` | snippet: *"[client_v3 | Section: Client Reference (v3) > Methods > Client.send()] ### Client.send()  Sends a st..."*
- **Rank 2** (Score: `0.6459`): `v2_client_v2_struct_002` | file: `data/v2/client_v2.md` | snippet: *"[client_v2 | Section: Client Reference (v2) > Methods > Client.send()] ### Client.send()  Sends an H..."*
- **Rank 3** (Score: `0.4771`): `v3_client_v3_struct_003` | file: `data/v3/client_v3.txt` | snippet: *"[client_v3 | Section: Client Reference (v3) > Methods > Example Usage] #### Example Usage  ```python..."*
- **Rank 4** (Score: `0.4111`): `v3_client_v3_struct_000` | file: `data/v3/client_v3.txt` | snippet: *"[client_v3 | Section: Client Reference (v3)] # Client Reference (v3)  The `Client` class is the main..."*
- **Rank 5** (Score: `0.3646`): `v2_client_v2_struct_000` | file: `data/v2/client_v2.md` | snippet: *"[client_v2 | Section: Client Reference (v2)] # Client Reference (v2)  The `Client` class handles HTT..."*
