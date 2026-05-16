# Sample AI Agents with Knowledge Graph Memory

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![SurrealDB](https://img.shields.io/badge/SurrealDB-v2.0%2B-ff00a0)
![OpenAI](https://img.shields.io/badge/OpenAI-API-412991)
![License](https://img.shields.io/badge/License-MIT-green)

A hands-on collection of **sample AI agents** that demonstrate tool calling, framework-specific agent patterns, retrieval workflows, and knowledge-graph-backed memory using **SurrealDB**.

This repository is not only about memory. It is a practical playground for comparing how different agent frameworks implement similar capabilities, including OpenAI SDK, PydanticAI, LangChain, and LangGraph.

> 🌐 **Project Website:** https://agennext.github.io/Agent-Memory/

## What You’ll Find Here

- Sample agents built with multiple frameworks
- Tool-calling examples for retrieval and reasoning
- Knowledge graph memory patterns with SurrealDB
- Vector search and hybrid retrieval examples
- Decision tracing for agent observability
- Temporal facts for historical context
- Docker-based local development setup

## Sample Agents

| File | Framework | What it demonstrates |
| --- | --- | --- |
| `agent.py` | OpenAI SDK | Raw tool-calling loop and direct control over agent execution |
| `agent_pydantic.py` | PydanticAI | Typed agent patterns and structured tool usage |
| `agent_langchain.py` | LangChain | LangChain tools and agent orchestration |
| `agent_langgraph.py` | LangGraph | Graph-based workflow with an enforced review step |

Each sample agent works with the same underlying memory and retrieval concepts, making it easier to compare framework ergonomics and tradeoffs.

## Framework Comparison

The sample agents implement the same core support-agent workflow in different frameworks:

1. Review similar past decisions.
2. Search relevant knowledge-base articles.
3. Traverse related products, tickets, and solutions.
4. Produce a clear support answer.
5. Trace the reasoning and retrieval steps.

This makes it easier to compare how each framework stacks up for the same task.

| Dimension | OpenAI SDK | PydanticAI | LangChain | LangGraph |
| --- | --- | --- | --- | --- |
| Main style | Low-level, explicit tool-calling loop | Typed agent abstraction | Tool and chain orchestration | Explicit graph/state-machine workflow |
| Best for | Maximum control and transparency | Type safety and structured outputs | Ecosystem integrations and familiar abstractions | Multi-step workflows with enforced control flow |
| Tool definition | Manual functions and tool schemas | Python functions with Pydantic models | LangChain tool wrappers | Nodes and edges in a graph workflow |
| Control flow | Fully manual | Mostly agent-managed | Agent/executor-managed | Explicit state transitions |
| Structured outputs | Manual parsing and validation | First-class Pydantic models | Available through LangChain patterns | Defined through graph state and node contracts |
| Observability | Custom tracing is easy to wire directly | Tracing can be attached around typed tools | Uses LangChain callbacks/tracing patterns | State transitions make workflow tracing natural |
| Boilerplate | Higher | Moderate | Moderate | Higher upfront, cleaner for complex flows |
| Learning curve | Lowest if you know raw APIs | Moderate | Moderate | Highest, but powerful for workflows |
| When to choose it | You want full control over every model/tool call | You want safer schemas and typed results | You want a broad agent/tooling ecosystem | You need deterministic multi-step agent flows |

### How to Compare Them Locally

Run each implementation with the same prompt and compare the code and output:

```bash
uv run python agent.py
uv run python agent_pydantic.py
uv run python agent_langchain.py
uv run python agent_langgraph.py
```

Use the same demo question each time:

```text
How do I set up authentication?
```

Then compare:

- How much code is needed to define tools
- How easy the control flow is to understand
- How strictly outputs are typed or validated
- How easy it is to add tracing
- How easy it is to enforce a specific workflow
- How framework-specific the implementation feels
- How easy it would be to extend the agent with more tools

## Knowledge Graph Memory Layer

The agents use SurrealDB as a shared memory and retrieval layer. This gives them access to:

- **Entities and relationships** across articles, products, tickets, customers, and solutions
- **Vector search** for semantic similarity
- **Graph traversal** for relationship-aware retrieval
- **Decision traces** for debugging and auditability
- **Temporal facts** for asking what was true at a given time

## Architecture

```text
┌─────────────────────────────────────────────────────────┐
│                 Sample Agent Implementations            │
│                                                         │
│  OpenAI SDK • PydanticAI • LangChain • LangGraph         │
│                                                         │
│  Tool calling • Reasoning loops • Review workflows       │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                 Shared Retrieval + Memory Layer         │
│                                                         │
│  SurrealDB knowledge graph + vector indexes             │
│                                                         │
│  [Article] ──references──▶ [Product]                    │
│      │                         ▲                        │
│      │                         │                        │
│      ▼                         │ about                  │
│  [Ticket] ──resolved_by──▶ [Solution]                   │
│      │                                                  │
│      └──authored──▶ [Customer]                          │
│                                                         │
│  + Vector search                                        │
│  + Graph traversal                                      │
│  + Decision tracing                                     │
│  + Temporal context                                     │
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

Copy the example environment file:

```bash
cp .env.example .env
```

Then add your API key:

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

### 6. Run a sample agent

```bash
uv run python agent.py
```

You can also try the framework-specific variants:

```bash
uv run python agent_pydantic.py
uv run python agent_langchain.py
uv run python agent_langgraph.py
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
├── docs/                    # Diagrams and documentation assets
├── tests/                   # Smoke tests and future test coverage
├── pyproject.toml           # Python project and dependencies
└── README.md
```

## Retrieval and Memory Features

### Hybrid retrieval

Combine semantic search and graph traversal in one shared layer.

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

## Demo Questions

After loading the sample data, try:

- `How do I set up authentication?`
- `What products support SSO?`
- `Show me solutions for the auth product.`
- `Have we seen this issue before?`
- `What past decisions led to this recommendation?`

## When to Use These Examples

Use this repository when you want to:

- Compare agent framework implementations side by side
- Learn practical tool-calling patterns
- Build agents that retrieve from structured and semantic memory
- Prototype customer support, developer assistant, or internal knowledge agents
- Explore graph-plus-vector retrieval with SurrealDB
- Add observability and decision tracing to agent workflows

## Roadmap Ideas

- Add more sample agents for additional frameworks
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
