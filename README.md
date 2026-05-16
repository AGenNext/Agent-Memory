# Agent Memory with Knowledge Graphs

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![SurrealDB](https://img.shields.io/badge/SurrealDB-v2.0%2B-ff00a0)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991)
![License](https://img.shields.io/badge/License-MIT-green)

A demo project for building production-style AI agent memory with **knowledge graphs**, **vector search**, and **decision tracing** in **SurrealDB**.

This repository shows how an agent can store durable context, retrieve relevant knowledge, follow relationships between entities, and audit the reasoning path that led to an answer.

## Highlights

- Knowledge graph memory for connected entities and relationships
- Vector search for semantic retrieval
- Hybrid retrieval that combines graph traversal and embeddings
- Decision tracing for observability and auditability
- Temporal facts for querying historical context
- Multiple agent implementations using OpenAI SDK, PydanticAI, LangChain, and LangGraph

## What This Project Demonstrates

Agent memory is a persistent, queryable layer that helps AI agents move beyond single-session context windows. With the patterns in this repo, an agent can:

- **Accumulate context** across conversations and support requests
- **Maintain entity awareness** with graph relationships between articles, products, tickets, customers, and solutions
- **Retrieve semantically similar knowledge** with vector search
- **Reason across relationships** with graph traversal
- **Trace decisions over time** for debugging and auditability
- **Coordinate shared memory** across multiple agents or workflows

## Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                    AI Agent / LLM                      │
│                                                         │
│  Tool-calling + reasoning loop                          │
│  • review_past_decisions                                │
│  • search_articles       vector search                  │
│  • find_related          graph traversal                │
│  • find_solutions        hybrid retrieval               │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                       SurrealDB                         │
│                                                         │
│  Knowledge graph + vector indexes                       │
│                                                         │
│  [Article] ──references──▶ [Product]                    │
│      │                         ▲                        │
│      │                         │                        │
│      ▼                         │ about                  │
│  [Ticket] ──resolved_by──▶ [Solution]                   │
│      │                                                  │
│      └──authored──▶ [Customer]                          │
│                                                         │
│  + Vector index for semantic search                     │
│  + Decision traces for auditing                         │
│  + Temporal facts for historical context                │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- **SurrealDB** nightly or v2.0+
- **uv** Python package manager
- **OpenAI API key** for embeddings and LLM calls
- **Docker Compose** optional, for local SurrealDB and Surrealist UI

Install `uv` if needed:

```bash
pip install uv
```

## Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/AGenNext/Agent-Memory.git
cd Agent-Memory
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure your environment

Create a `.env` file and add your OpenAI API key:

```bash
OPENAI_API_KEY=your_api_key_here
```

### 4. Start SurrealDB

For a fast local demo with in-memory storage:

```bash
surreal start \
  --log trace \
  --user root \
  --pass root \
  --allow-funcs \
  --allow-net \
  --allow-experimental \
  memory
```

### 5. Load schema, sample data, and embeddings

```bash
uv run python load.py
```

### 6. Run an agent

```bash
uv run python agent.py
```

Try asking:

```text
How do I set up authentication?
```

## Storage Modes

SurrealDB can run in several modes depending on whether you want a quick demo, local persistence, or a distributed deployment.

### In-memory

Fastest option. Data is cleared when the database stops.

```bash
surreal start --user root --pass root memory
```

### RocksDB file-backed storage

Good default for local persistent storage.

```bash
surreal start --user root --pass root rocksdb:///data/memory.db
```

### SurrealKV file-backed storage

Modern embedded storage option.

```bash
surreal start --user root --pass root surrealkv:///data/memory.db
```

### TiKV distributed storage

Use this when testing distributed deployments.

```bash
# Start TiKV first
tiup playground --tag surrealdb --mode tikv-slim --pd 1 --kv 1

# Then start SurrealDB with TiKV
surreal start --user root --pass root tikv://127.0.0.1:2379
```

## Docker Compose

Start SurrealDB only:

```bash
docker-compose up -d surrealdb
```

Start SurrealDB with the Surrealist web UI:

```bash
docker-compose up -d surrealdb surrealist
```

Start the distributed TiKV setup:

```bash
docker-compose -f docker-compose.yml up -d pd tikv surrealdb-tikv
```

## Surrealist Web UI

After starting Surrealist, open:

- **URL:** `http://localhost:3000`
- **Namespace / database:** `memory / agent`
- **User:** `root`
- **Password:** `root`

Useful views in Surrealist:

- **Query View** for running SurrealQL queries
- **Graph View** for visualizing entity relationships
- **Table Explorer** for browsing records
- **Schema Designer** for inspecting tables and fields
- **Live Queries** for real-time updates
- **Authentication** for managing users and scopes

## Project Structure

```text
Agent-Memory/
├── surql/
│   ├── 01-schema.surql      # Tables, fields, and vector indexes
│   ├── 02-ingest.surql      # Sample data and graph edges
│   └── 03-query.surql       # Retrieval examples and query patterns
├── agent.py                 # OpenAI SDK agent with raw tool calling
├── agent_pydantic.py        # PydanticAI implementation
├── agent_langchain.py       # LangChain implementation
├── agent_langgraph.py       # LangGraph implementation with review flow
├── load.py                  # Loads schema, data, and embeddings
├── pyproject.toml           # Python project and dependencies
└── README.md
```

## Key Features

### Hybrid retrieval

Combine semantic search and graph traversal in one memory layer.

```sql
-- Vector search for similar articles
SELECT id, title, vector::distance::knn() AS distance
FROM article
WHERE embedding <|5,100|> $query;

-- Graph traversal from product to related solutions
SELECT
  name,
  <-about<-ticket->resolved_by->solution.{title, steps}
FROM product:auth;
```

### Decision tracing

Trace every important agent step for review and debugging.

```text
session:abc123
├── decision_step:001 "receive_query"
├── led_to
├── decision_step:002 "tool_call: search_articles"
├── led_to
├── decision_step:003 "tool_call: find_related"
├── led_to
├── decision_step:004 "answer"
└── produced
    └── response_trace:001
```

### Temporal facts

Ask what was true at a specific point in time.

```sql
SELECT * FROM solution
WHERE created < $point_in_time
AND (valid_until IS NONE OR valid_until > $point_in_time);
```

### Multiple agent implementations

| File | Framework | Description |
| --- | --- | --- |
| `agent.py` | OpenAI SDK | Raw tool-calling loop |
| `agent_pydantic.py` | PydanticAI | Pydantic-based agent implementation |
| `agent_langchain.py` | LangChain | LangChain tools implementation |
| `agent_langgraph.py` | LangGraph | Agent workflow with an enforced review step |

## Demo Questions

After loading the sample data, try:

- `How do I set up authentication?`
- `What products support SSO?`
- `Show me solutions for the auth product.`
- `Have we seen this issue before?`
- `What past decisions led to this recommendation?`

## When to Use This Pattern

This architecture is useful when your agent needs to remember more than isolated chat history, especially for:

- Customer support copilots
- Developer assistants
- Internal knowledge agents
- Product operations agents
- Multi-agent systems that share context
- Auditable AI workflows

## Roadmap Ideas

- Add more realistic support-ticket and knowledge-base datasets
- Add automated tests for retrieval flows
- Add benchmark scripts for vector-only vs graph-plus-vector retrieval
- Add deployment examples for production SurrealDB setups
- Add a hosted demo or walkthrough video

## Contributing

Contributions are welcome. Please see [CONTRIBUTING.md](CONTRIBUTING.md) for setup steps, development workflow, and pull request guidelines.

## License

This project is released under the [MIT License](LICENSE).

## See Also

- [SurrealDB knowledge graph tutorial](https://surrealdb.com/docs/explore/tutorials/tutorials/how-to-build-a-knowledge-graph-for-ai)
- [Spectron - Agent Memory](https://surrealdb.com/platform/spectron)
- [SurrealDB University](https://surrealdb.com/blog/category/tutorials)
