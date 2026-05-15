# SurrealDB Tools & Capabilities

Tools, capabilities, and built-in features.

## Tools

| Tool | File | Description |
|------|------|-------------|
| **Functions** | `tools/functions.py` | SurrealQL functions |
| **LIVE Queries** | `tools/live_queries.py` | Real-time subscriptions |
| **Vector Search** | `tools/vector_search.py` | KNN & similarity |
| **Full-Text** | `tools/fulltext_search.py` | BM25 & highlight |
| **Streaming** | `tools/streaming.py` | WebSocket streaming |
| **RPC** | `tools/rpc.py` | Remote procedure calls |

## Usage

### Functions
```python
from tools.functions import SurrealQLFunctions

fns = SurrealQLFunctions()
await fns.connect()

await fns.string_upper("hello")
await fns.math_mean([1, 2, 3])
await fns.time_now()
```

### LIVE Queries
```python
from tools.live_queries import LiveQueryTool

live = LiveQueryTool()
await live.connect()

async for change in live.watch_table("message"):
    print(change)

async for change in live.watch_chat_room("general"):
    print(change["content"])
```

### Streaming
```python
from tools.streaming import StreamingTool

stream = StreamingTool()
await stream.connect()

async for msg in stream.stream_chat("general"):
    print(msg)

async for data in stream.stream_telemetry("sensor_1"):
    print(data)
```

### RPC
```python
from tools.rpc import RPCTool

rpc = RPCTool()
await rpc.connect()

await rpc.create("user", {"name": "Alice"})
await rpc.relate("user:alice", "user:bob", "follows")
await rpc.call_function("math::sum", [1, 2, 3])
```