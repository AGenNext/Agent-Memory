# Kai G Agent - SurrealDB AI Agent

Based on: https://github.com/surrealdb/kaig

## What is Kai G?

AI agent that handles database needs with SurrealDB:
- Vector search
- Graph queries
- Knowledge graphs
- Text-to-SurrealQL

## Installation

```bash
pip install kaig
# Or
git clone https://github.com/surrealdb/kaig.git
```

## Quick Start

```python
from kaig.db import DB
from kaig.llm import LLM, Embedder

# Setup
db = DB(
    url="ws://localhost:8000/rpc",
    username="root",
    password="root",
    namespace="memory",
    database="agent",
    embedder=Embedder(provider="ollama", model_name="all-minilm"),
    llm=LLM(provider="ollama", model_name="llama3.2"),
    vector_tables=[
        VectorTableDefinition("document", "COSINE"),
    ],
    graph_relations=[
        Relation("has_keyword", "document", "keyword"),
    ],
)

db.apply_schemas()
```

## Agent Example

```python
from pydantic_ai import Agent
from kaig.db import DB
from knowledge_graph.tools import fs, query_db

# Create agent
agent = Agent(
    model="ollama:llama3.2",
    tools=[
        fs.read_file,
        fs.write_file,
        query_db.query_db,
    ],
)

# Run
result = agent.run("List all documents about AI")
print(result)
```

## Features

| Feature | Description |
|---------|-------------|
| **Vector Search** | Semantic search with embeddings |
| **Knowledge Graph** | Entity relationships |
| **Text-to-SurrealQL** | Natural language to queries |
| **File System** | Virtual file storage in DB |
| **RAG Pipeline** | Document ingestion & chunking |

## Tools

- `query_db` - Query database with natural language
- `fs.read_file` - Read file from virtual FS
- `fs.write_file` - Write file to virtual FS
- `ingest` - Ingest documents

## Example Commands

> "Find all documents related to AI"
> "Create a file with product reviews"
> "Show customers who bought tech products"

## Demo App

```bash
cd kaig-app
npm install
npm run dev
```

## Resources

- [GitHub](https://github.com/surrealdb/kaig)
- [Examples](https://github.com/surrealdb/kaig/tree/main/examples)