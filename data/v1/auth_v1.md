# Auth Reference (v1)

The `Auth` class handles basic password authentication for the original v1 SDK release.

## Methods

### Auth.login()

Simple username/password authentication returning a bearer token with default read-only scope.

| Parameter | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `username` | `str` | `None` | `true` | Account username for v1 legacy authentication. |
| `scopes` | `list[str]` | `["read"]` | `true` | Authorization scope list for v1 session tokens. |
| `token_ttl_sec` | `int` | `1800` | `false` | Token expiration in seconds for v1 (30 minutes). |

```python
auth = Auth(auth_url="https://auth-v1.example.com")
token = auth.login(username="admin@company.com", scopes=["read"], token_ttl_sec=1800)
```
