# SurrealDB Tools & Capabilities

Tools, capabilities, and built-in features.

## Tools

| Tool | File | Description |
|------|------|-------------|
| **Functions** | `tools/functions.py` | SurrealQL functions |
| **LIVE Queries** | `tools/live_queries.py` | Real-time subscriptions |
| **Vector Search** | `tools/vector_search.py` | KNN & similarity |
| **Full-Text** | `tools/fulltext_search.py` | BM25 & highlight |

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

### Vector Search
```python
from tools.vector_search import VectorSearchTool

vs = VectorSearchTool()
await vs.connect()

await vs.create_index("doc", "embedding", 384)
results = await vs.knn("doc", query_vector, k=5)
```

### Full-Text Search
```python
from tools.fulltext_search import FullTextSearchTool

fts = FullTextSearchTool()
await fts.connect()

await fts.create_analyzer("en")
await fts.search("article", "AI", k=10)
```

## Core Capabilities

| Feature | Description |
|---------|-------------|
| **LIVE Queries** | Subscribe to changes without polling |
| **Events** | TABLE/FIELD triggers |
| **Vector Search** | HNSW indexes, KNN |
| **Full-Text** | BM25, highlight |
| **Graph Relations** | RELATE tables |
| **Functions** | 50+ built-in |

## Features from Docs

- https://surrealdb.com/use-cases/real-time
- https://surrealdb.com/docs/surrealql/functions
- https://surrealdb.com/docs/surrealql/datamodel/vector