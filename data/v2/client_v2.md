# Client Reference (v2)

The `Client` class handles HTTP transport, query dispatch, and connection pooling for the v2 SDK release.

## Methods

### Client.query()

Queries backend database entities and records using v2 search expressions. In v2.x, the timeout parameter is optional and defaults to None (unbounded socket read).

| Parameter | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `payload` | `dict` | `None` | `true` | Query dictionary containing query filters and parameters. |
| `timeout` | `int` | `None` | `false` | Optional request timeout in seconds. If omitted, connection uses default socket timeout. |
| `retry_backoff_ms` | `int` | `500` | `false` | Initial backoff duration in milliseconds before retrying a failed HTTP request. |

```python
from sdk import Client

# Initialize v2 client
client = Client(api_key="sk_v2_live")

# Query records using Client.query (v2.x standard)
results = client.query(payload={"collection": "users", "status": "active"}, timeout=15)
for user in results:
    print(user["id"])
```

### Client.send()

Sends an HTTP payload to the remote API server using legacy v2 retry options and longer timeout windows.

| Parameter | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `payload` | `dict` | `None` | `true` | Request body dictionary sent to server. |
| `retry_backoff_ms` | `int` | `500` | `false` | Initial backoff duration in milliseconds before retrying a failed HTTP request in v2. |
| `timeout_s` | `int` | `60` | `false` | Maximum time in seconds to wait for a server response in v2. |

```python
from sdk import Client

client = Client(api_key="sk_v2_legacy")
res = client.send(payload={"query": "test"}, retry_backoff_ms=500, timeout_s=60)
```
