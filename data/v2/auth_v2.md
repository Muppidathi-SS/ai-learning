# Auth Reference (v2)

The `Auth` class provides user authentication and basic session management for the v2 SDK.

## Methods

### Auth.login()

Authenticates a user and returns a session token for API access using legacy v2 auth flow.

| Parameter | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `username` | `str` | `None` | `true` | The account email or username string for authentication. |
| `scopes` | `list[str]` | `["read"]` | `true` | List of requested authorization scope permissions for the v2 session. |
| `token_ttl_sec` | `int` | `7200` | `false` | Time-to-live for issued tokens in seconds in v2 (longer default than v3). |

```python
auth = Auth(auth_url="https://auth-v2.example.com")
token = auth.login(username="admin@company.com", scopes=["read"], token_ttl_sec=7200)
```
