# Building Agent Memory with Knowledge Graphs

Demo code for building production agent memory using knowledge graphs and vectors in SurrealDB.

## What is Agent Memory?

Agent memory is a persistent, queryable memory layer that enables AI agents to:

- **Accumulate context** across conversations
- **Maintain entity awareness** through knowledge graphs  
- **Learn from past decisions** via temporal tracing
- **Coordinate with other agents** through shared memory

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (LLM)                      │
│  ┌─────────────────────────────────────────────────┐  │
│  │     Tool Calling + Reasoning Loop              │  │
│  │  • review_past_decisions               │  │
│  │  • search_articles (vector search)       │  │
│  │  • find_related (graph traversal)      │  │
│  │  • find_solutions (hybrid retrieval)    │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   SurrealDB                            │
│  ┌─────────────────────────────────────────────────┐  │
│  │     Knowledge Graph + Vectors                  │  │
│  │                                              │  │
│  │  [Article] ──references──▶ [Product]        │  │
│  │     │                       ▲               │  │
│  │     │                       │               │  │
│  │    │▼              about──┘                │  │
│  │    ▼                    │                    │  │
│  │  [Ticket] ──resolved_by▶ [Solution]        │  │
│  │     │                                         │  │
│  │     └──authored──▶ [Customer]                │  │
│  │                                              │  │
│  │  + Vector Index for semantic search            │  │
│  │  + Decision traces for auditing                │  │
│  └─────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

- **SurrealDB** (nightly or v2.0+) - Start with: `surreal start --log trace --user root --pass root --allow-funcs --allow-net --allow-experimental memory`
- **uv** - Python package manager (install via `pip install uv`)
- **OpenAI API key** - For embeddings and LLM

## Quick Start

1. **Clone and setup:**
   ```bash
   cd Agent-Memory
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

2. **Start SurrealDB + Surrealist UI:**
   ```bash
   docker-compose up -d surrealdb surrealist
   # Open http://localhost:3000 in browser
   ```

3. **Load schema + data:**
   ```bash
   uv sync
   uv run load.py
   ```

4. **Run the agent:**
   ```bash
   uv run agent.py
   ```

## Surrealist Web UI

After running `docker-compose up`, access the Surrealist UI at:

- **URL:** http://localhost:3000
- **Database:** `memory/agent` (namespace/database)
- **User:** `root`
- **Pass:** `root`

### Surrealist Features:
- **Query View** - Run SurrealQL queries with tabs
- **Graph View** - Visualize entity relationships
- **Table Explorer** - Browse records visually
- **Schema Designer** - Create tables/fields
- **Live Queries** - Real-time updates
- **Authentication** - Manage users/scopes

## Project Structure

```
agent-memory/
├── surql/
│   ├── 01-schema.surql      # Tables, fields, vector indexes
│   ├── 02-ingest.surql     # Sample data and graph edges
│   └── 03-query.surql      # Retrieval patterns
├── agent.py                # Python agent with tool-calling
├── load.py                # Load schema + data + embeddings
├── pyproject.toml         # Dependencies
└── README.md
```

## Key Features

### 1. Hybrid Retrieval

Combine vector search + graph traversal in one query:

```sql
-- Vector search for similar articles
SELECT id, title, vector::distance::knn() AS distance
FROM article
WHERE embedding <|5,100|> $query;

-- Graph traversal from product to solutions
SELECT 
    name,
    <-about<-ticket->resolved_by->solution.{title, steps}
FROM product:auth;
```

### 2. Decision Tracing

Every agent decision is traced for auditing:

```
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

### 3. Temporal Facts

Track what was true at any point:

```sql
-- Historical solutions (what was valid at time X)
SELECT * FROM solution
WHERE created < $point_in_time
AND (valid_until IS NONE OR valid_until > $point_in_time);
```

## Available Agent Implementations

| File | Framework | Description |
|------|----------|-----------|
| `agent.py` | OpenAI SDK | Raw tool-calling loop |
| `agent_pydantic.py` | PydanticAI | Pydantic-based agents |
| `agent_langchain.py` | LangChain | LangChain tools |
| `agent_langgraph.py` | LangGraph | Enforced review flow |

## Demo Questions to Try

After loading data:

- "How do I set up authentication?"
- "What products support SSO?"
- "Show me solutions for the auth product"
- "Have we seen this issue before?"

## See Also

- [SurrealDB Knowledge Graph Tutorial](https://surrealdb.com/docs/explore/tutorials/tutorials/how-to-build-a-knowledge-graph-for-ai)
- [Spectron - Agent Memory](https://surrealdb.com/platform/spectron)
- [SurrealDB University](https://surrealdb.com/blog/category/tutorials)