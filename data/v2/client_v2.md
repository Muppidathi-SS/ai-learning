# Client Reference (v2)

The `Client` class handles HTTP transport and connection pooling for the v2 SDK release.

## Methods

### Client.send()

Sends an HTTP payload to the remote API server using legacy v2 retry options and longer timeout windows.

| Parameter | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `payload` | `dict` | `None` | `true` | Request body dictionary sent to server. |
| `retry_backoff_ms` | `int` | `500` | `false` | Initial backoff duration in milliseconds before retrying a failed HTTP request in v2. |
| `timeout_s` | `int` | `60` | `false` | Maximum time in seconds to wait for a server response in v2. |

```python
client = Client(api_key="sk_v2_legacy")
res = client.send(payload={"query": "test"}, retry_backoff_ms=500, timeout_s=60)
```
