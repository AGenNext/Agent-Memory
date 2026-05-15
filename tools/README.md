# SurrealDB Tools & Capabilities

Tools, capabilities, and built-in features.

## UI

Open `ui/index.html` in a browser for a complete dashboard with:

- Vector Search interface
- Knowledge Graph explorer
- RAG Chat
- Live Queries (real-time)
- AI Agent Chat
- Healthcare Agent
- Finance Agent
- Gaming Agent
- Schema Editor
- Query Editor
- Data Explorer

## Tools

| Tool | File | Description |
|------|------|-------------|
| **Functions** | `tools/functions.py` | SurrealQL functions |
| **LIVE Queries** | `tools/live_queries.py` | Real-time subscriptions |
| **Streaming** | `tools/streaming.py` | WebSocket streaming |
| **Vector Search** | `tools/vector_search.py` | KNN & similarity |
| **Full-Text** | `tools/fulltext_search.py` | BM25 & highlight |
| **RPC** | `tools/rpc.py` | Remote procedure calls |
| **Knowledge Graph** | `tools/knowledge_graph.py` | Graph & ontological modeling |

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

### Knowledge Graph
```python
from tools.knowledge_graph import KnowledgeGraphTool

kg = KnowledgeGraphTool()
await kg.connect()

# Define ontology
await kg.define_entity("person", {"name": "string", "role": "string"})
await kg.define_relation("knows", "person", "person", {"confidence": "float"})

# Create nodes & edges
await kg.create_node("person", {"name": "Alice"})
await kg.relate("person:alice", "person:bob", "knows", {"confidence": 0.9})

# Traverse & filter
contacts = await kg.trusted_contacts("person:alice", "knows", 0.9)
```