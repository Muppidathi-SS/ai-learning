# Stream Reference (v2)

The `Stream` class handles basic event streaming over WebSocket connections in the v2 SDK.

## Methods

### Stream.subscribe()

Opens a WebSocket channel subscription with v2 buffering and heartbeat defaults.

| Parameter | Type | Default | Required | Description |
| :--- | :--- | :--- | :--- | :--- |
| `channel_name` | `str` | `None` | `true` | WebSocket channel name to subscribe to. |
| `max_buffer_size` | `int` | `512` | `false` | Maximum queued messages in the v2 buffer (smaller than v3). |
| `keep_alive_ping_ms` | `int` | `10000` | `false` | Heartbeat ping interval in milliseconds for v2 (10 seconds). |

```python
stream = Stream(endpoint="wss://stream-v2.example.com")
subscription = stream.subscribe(channel_name="events", max_buffer_size=512, keep_alive_ping_ms=10000)
```
