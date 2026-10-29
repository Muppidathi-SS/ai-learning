# Migration Guide: Upgrading from SDK v2.x to v3.0

This migration guide covers breaking architectural changes between SDK v2.x and v3.0.
Approximately 40% of developers remain on v2.x. If your production service is on v2.x, **do not copy v3 code snippets**, as method renames and mandatory parameters will cause runtime errors.

---

## 1. Executive Summary of Breaking Changes

| v2.x Legacy Interface | v3.0 Modern Interface | Nature of Change | Breaking Severity |
| :--- | :--- | :--- | :---: |
| `client.query(payload, timeout=None)` | `client.search(payload, timeout=30)` | Method renamed; `timeout` is now **MANDATORY** | 🚨 **CRITICAL** |
| `Stream.feed(channel, buffer_len, ping_interval)` | `Stream.subscribe(channel_name, max_buffer_size, keep_alive_ping_ms)` | Method renamed, params renamed | 🚨 **CRITICAL** |
| `Batch.dispatch(payloads, concurrency)` | `Batch.submit_jobs(job_list, max_concurrency)` | Method renamed, params renamed | 🚨 **CRITICAL** |
| `Auth.login(username, password)` | `client.auth(token_ttl_sec=3600)` | Direct login endpoint replaced with OAuth token issuance | 🚨 **CRITICAL** |
| `Config.get_config(path)` | `Config.load_settings(file_path, env_override=True)` | Method renamed, env overrides supported | ⚠️ Medium |
| `Webhook.subscribe(callback_url)` | `Webhook.register_listener(target_url, signature_algorithm)` | Requires cryptographic signature spec | ⚠️ Medium |

---

## 2. Breaking Method: `Client.query()` -> `Client.search()`

### The Problem
In v2.x, queries were dispatched via `client.query()` with optional timeout. In v3.0:
1. `Client.query()` was completely removed. Calling it raises `AttributeError: 'Client' object has no attribute 'query'. Did you mean 'search'?`
2. `Client.search()` requires an explicit `timeout` integer argument. Omitting `timeout` raises `ValueError: timeout parameter is mandatory in v3.0 Client.search()`.

### Code Comparison

#### v2.x (Legacy)
```python
from sdk import Client

client = Client(api_key="sk_v2_key")
# Optional timeout, defaults to None
results = client.query(payload={"user_id": "usr_9988"})
```

#### v3.0 (Modern)
```python
from sdk import Client

client = Client(api_key="sk_live_v3_key")
# MANDATORY timeout required!
results = client.search(payload={"user_id": "usr_9988"}, timeout=30)
```

---

## 3. Breaking Method: `Stream.feed()` -> `Stream.subscribe()`

### The Problem
`Stream.feed()` was removed in v3.0 in favor of standard WebSocket subscription semantics.

#### v2.x (Legacy)
```python
from sdk import Stream

stream = Stream.feed(channel="telemetry", buffer_len=512, ping_interval=10000)
for msg in stream:
    process(msg)
```

#### v3.0 (Modern)
```python
from sdk import Stream

stream = Stream.subscribe(channel_name="telemetry", max_buffer_size=1024, keep_alive_ping_ms=5000)
for msg in stream:
    process(msg)
```

---

## 4. Breaking Method: `Batch.dispatch()` -> `Batch.submit_jobs()`

#### v2.x (Legacy)
```python
from sdk import Batch

batch = Batch.dispatch(payloads=[{"id": 1}, {"id": 2}], concurrency=5)
```

#### v3.0 (Modern)
```python
from sdk import Batch

batch = Batch.submit_jobs(job_list=[{"id": 1}, {"id": 2}], max_concurrency=10, auto_retry_failed=True)
```
