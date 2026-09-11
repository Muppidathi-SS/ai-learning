# Client Reference (v1)

The `Client` class provides basic HTTP transport for the original v1 SDK release. This is the legacy implementation before connection pooling was introduced.

## Methods

### Client.send()

Sends an HTTP payload to the remote API server using legacy v1 retry timing and generous timeout defaults.

| Parameter | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `payload` | `dict` | `None` | `true` | Request body dictionary sent to server. |
| `retry_backoff_ms` | `int` | `1000` | `false` | Initial backoff duration in milliseconds before retrying a failed HTTP request in v1. |
| `timeout_s` | `int` | `120` | `false` | Maximum time in seconds to wait for a server response in v1. |

```python
client = Client(api_key="sk_v1_legacy_old")
res = client.send(payload={"query": "test"}, retry_backoff_ms=1000, timeout_s=120)
```
