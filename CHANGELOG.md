# SDK Changelog & Migration History

All notable changes to the Developer SDK are documented in this file.
This SDK follows Semantic Versioning (`MAJOR.MINOR.PATCH`).

---

## [3.0.0] - 2026-01-15 (Current Major Release - 60% of Integrators)

### 🚨 BREAKING CHANGES & REMOVALS

- **`Client.query()` Removed**:
  - The `Client.query()` method has been completely **REMOVED**.
  - Calling `client.query()` raises `AttributeError: 'Client' object has no attribute 'query'. Did you mean 'search'?`
  - Replaced by `Client.search(payload=..., timeout=...)`.
  - **Mandatory Timeout**: In `Client.search()`, the `timeout` argument is now **strictly mandatory**. Omitting `timeout` raises `ValueError: timeout parameter is mandatory in v3.0 Client.search()`. Unbounded socket queries are no longer permitted.

- **`Stream.feed()` Removed**:
  - `Stream.feed()` has been completely **REMOVED**.
  - Replaced by `Stream.subscribe(channel_name=..., max_buffer_size=1024, keep_alive_ping_ms=5000)`.
  - Parameter `buffer_len` renamed to `max_buffer_size` (default 1024).
  - Parameter `ping_interval` renamed to `keep_alive_ping_ms` (default 5000ms).

- **`Batch.dispatch()` Removed**:
  - `Batch.dispatch()` has been completely **REMOVED**.
  - Replaced by `Batch.submit_jobs(job_list=..., max_concurrency=10, auto_retry_failed=True)`.
  - Parameter `payloads` renamed to `job_list`.
  - Parameter `concurrency` renamed to `max_concurrency`.

- **`Auth.login()` Removed**:
  - `Auth.login()` and legacy cookie-based sessions have been removed.
  - Replaced by OAuth2 token authorization via `Client.auth(token_ttl_sec=3600)`.
  - REST endpoint `/v2/auth/login` sunsetted in favor of `/v3/auth/token`.

- **`Config.get_config()` Removed**:
  - `Config.get_config()` has been removed.
  - Replaced by `Config.load_settings(file_path=..., env_override=True)`.

- **`Webhook.subscribe()` Removed**:
  - `Webhook.subscribe()` has been removed.
  - Replaced by `Webhook.register_listener(target_url=..., signature_algorithm='HMAC-SHA256')`.

### ⚡ Performance & Transport Enhancements
- Default retry backoff reduced from 500ms to 250ms (`retry_backoff_ms=250`).
- HTTP/2 multiplexed connection pool enabled by default.

---

## [2.4.0] - 2025-06-10 (Current LTS Release - 40% of Integrators)

### Deprecations
- **Deprecation Notice**: `Client.query()` is deprecated and scheduled for removal in v3.0.0. Integrators should prepare to migrate to `Client.search()` with explicit timeouts.
- **Deprecation Notice**: `Stream.feed()` is deprecated; will be replaced by `Stream.subscribe()` in v3.0.0.
- **Deprecation Notice**: `Batch.dispatch()` is deprecated; will be replaced by `Batch.submit_jobs()` in v3.0.0.
- **Deprecation Notice**: `Auth.login()` is deprecated; will be replaced by scoped token issuance (`/v3/auth/token`).

### Features
- Added connection health checks to `Client.send()`.
- Added telemetry buffer metrics.

---

## [2.0.0] - 2024-03-20

### Breaking Changes
- `Client.send()` parameter `timeout` renamed to `timeout_s` to enforce seconds notation.
- `Auth.login()` parameter `session_expiry` replaced with `token_ttl_sec`.
- Support for v1 legacy API keys (`sk_v1_...`) deprecated.
