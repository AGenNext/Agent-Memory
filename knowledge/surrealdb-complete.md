# SurrealDB Complete Knowledge

All topics organized from surrealdb.com main site and docs.

---

## Platform Products

| Product | Description |
|---------|-------------|
| **SurrealDB** | Multi-model database (documents, graph, vectors, SQL) |
| **Spectron** | AI agent memory - persistent, queryable |
| **Distributed Storage** | Horizontally scalable, consistent |
| **SurrealDB Cloud** | Managed, auto-scaling |
| **MCP** | Model Context Protocol |

---

## Client Libraries (SDKs)

- JavaScript
- Python  
- Rust
- Node.js
- WebAssembly
- Java
- Golang
- .NET
- PHP
- C

---

## Tools

- **SurrealDB Cloud** - Managed service
- **Surrealist** - Visual IDE/UI
- **Extensions** - Custom WASM functions
- **Integrations** - Connect with tools

---

## Resources

| Resource | Description |
|---------|-------------|
| **Labs** | Examples & integrations |
| **Sidekick** | SurrealQL AI Assistant |
| **University** | Beginner to expert |
| **Blog** | Blog posts |
| **Case studies** | Enterprise cases |
| **Events** | Webinars |
| **Ambassador** | Community program |

---

## Use Cases

- AI Agents (Agent Memory)
- Real-Time Applications
- Knowledge Graphs
- Embedded and Edge
- Industry solutions

---

## Industries

- Finance and FinTech
- Defence and aerospace
- Gaming and entertainment
- Energy and manufacturing
- Healthcare
- Retail and e-commerce

---

## Data Models

| Model | Description |
|-------|-------------|
| **Documents** | Nested JSON |
| **Graph** | Relationships |
| **Vectors** | Embeddings |
| **Time-series** | Temporal |
| **Full-text** | Search |

---

## Features

- Real-time queries (LIVE)
- Authentication & RBAC
- Graph relationships
- Vector search
- Schema migrations (SurrealKit)
- Surrealist UI

---

## Deployment Options

- SurrealDB Cloud (managed)
- Self-hosted (install)
- Docker containers
- Embedded (WASM)

---

## Documentation Sections

### Learn
- Querying
- Schema Management
- Data Models
- Security
- Agent Memory Context
- Extensions

### Languages
- Python
- JavaScript
- Go
- Rust
- Java
- .NET
- PHP

### Running
- In-memory
- File-backed (RocksDB, SurrealKV)
- Multi-node (TiKV)
- Docker

---

## SurrealQL Query Patterns

```sql
-- Hybrid RAG
LET $query = "question";
LET $emb = fn::embed($query);
LET $vs = SELECT id FROM doc WHERE embedding <|20|> $emb;
LET $ft = SELECT id FROM doc WHERE content @1@ $query;
SELECT * FROM search::rrf([$vs, $ft], 5, 60);

-- Graph RAG
LET $seeds = SELECT * FROM doc ...;
SELECT 
  id, 
  count(<-references<-doc[WHEREidIN$ids]) AS authority
FROM $seeds;

-- Knowledge Graph
RELATE entity:openai -> developed -> entity:gpt4;
SELECT ->developed->entity.name AS built FROM entity:openai;

-- Agent Memory
CREATE memory SET agent, content, embedding, created_at=time::now();
DEFINEEVENT ON memory WHEN $event = "CREATE" THEN ...

-- Conversational Memory
CREATE session SET user, started_at;
CREATE message SET role, content, embedding;
RELATE session -> contains -> message;

-- Live Queries
LIVE SELECT * FROM task WHERE assignee = $auth.id;
```

---

## Resources Links

- Docs: https://surrealdb.com/docs
- GitHub: github.com/surrealdb
- Discord: discord.gg/surrealdb
- Blog: https://surrealdb.com/blog
- Roadmap: https://surrealdb.com/roadmap