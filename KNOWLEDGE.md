# Agent Memory - Skills, Tools, Knowledge Base

This document organizes SurrealDB topics into skills, tools, knowledge, and prompts for the Agent Memory learning platform.

---

## 🔧 TOOLS (Build with)

### Core Database
| Tool | Description | Doc |
|------|-------------|-----|
| **SurrealDB** | Multi-model database (doc/graph/vector) | [docs](https://surrealdb.com/docs) |
| **SurrealKV** | Embedded key-value store (LSM tree) | [GitHub](https://github.com/surrealdb/surrealkv) |
| **TiKV** | Distributed storage | [docs](https://surrealdb.com/docs/self-hosted/multi-node) |

### Agent Memory
| Tool | Description | Doc |
|------|-------------|-----|
| **Spectron** | Built-in agent memory | [page](https://surrealdb.com/platform/spectron) |
| **Agent Memory SDK** | Python SDK for memory | [repo](https://github.com/AGenNext/Agent-Memory) |

### Development Tools
| Tool | Description | Doc |
|------|-------------|-----|
| **Surrealist** | Visual IDE/UI | [page](https://surrealdb.com/surrealist) |
| **SurrealKit** | Schema migrations & testing | [GitHub](https://github.com/surrealdb/surrealkit) |
| **SurrealML** | In-database ML inference | [docs](https://surrealdb.com/docs/explore/ml-models) |
| **CLI** | Command-line tools | [docs](https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview) |

### Deployment
| Tool | Description | Doc |
|------|-------------|-----|
| **SurrealDB Cloud** | Managed cloud service | [page](https://surrealdb.com/cloud) |
| **Docker** | Container deployment | [docs](https://surrealdb.com/docs/running/docker) |
| **WASM** | Browser/embedded | [docs](https://surrealdb.com/docs/embedding/javascript) |

### Integrations
| Tool | Description |
|------|-------------|
| **MCP** | Model Context Protocol |
| **SDKs** | Python, JS, Go, Rust, Java, .NET, PHP |
| **GraphQL** | GraphQL API |
| **REST** | HTTP API |

---

## 📚 KNOWLEDGE (Learn)

### Concepts
| Topic | Description |
|-------|-------------|
| **Multi-model** | Documents + Graph + Vectors + Time-series |
| **ACID** | Atomic, Consistent, Isolated, Durable |
| **MVCC** | Multi-version concurrency control |
| **LSM Tree** | Log-structured merge (SurrealKV) |
| **HNSW** | Hierarchical navigable small world (vectors) |
| **BM25** | Full-text search ranking |

### Comparisons
| Topic | What it compares |
|-------|-----------------|
| **vs Postgres** | Vector + graph native vs extensions |
| **vs MongoDB** | Graph + vectors vs document-only |
| **vs Neo4j** | Multi-model vs graph-only |
| **vs Vector DBs** | Entity context + vectors |
| **vs Memory Middleware** | ACID vs eventual consistency |

### Architecture
| Topic | Description |
|-------|-------------|
| **Context Layer** | Memory in the database |
| **Storage-compute** | Separation of concerns |
| **Replication** | Quorum-based fault tolerance |
| **Sharding** | Automatic data distribution |

---

## ⚡ PROMPTS (Use)

### Query Prompts
```sql
-- Full-text search
SELECT * FROM article WHERE content @1@ 'search term';

-- Vector similarity  
SELECT * FROM article WHERE embedding <|5|> $query;

-- Graph traversal
SELECT <-authored<-ticket FROM user:alice;

-- Live query
LIVE SELECT * FROM session WHERE status = 'active';

-- Hybrid search
SELECT search::rrf([$text_results, $vec_results], 5, 60);
```

### Admin Prompts
```sql
-- Start server
surreal start --user root --pass root memory

-- Create index
DEFINE INDEX idx ON table FIELDS field;

-- Schema migration
surrealkit sync

-- Run tests
surrealkit test
```

### Development Prompts
```python
# Connect to SurrealDB
from surrealdb import Surreal
db = Surreal('ws://localhost:8000/rpc')
await db.connect()

# Query
await db.query('SELECT * FROM session')
```

---

## 🎯 SKILLS (Abilities)

### Data Skills
| Skill | Description |
|-------|-------------|
| **Schema Design** | Define tables, fields, indexes |
| **Query Writing** | SurrealQL mastery |
| **Graph Modeling** | Entity relationships |
| **Vector Search** | Embeddings & similarity |
| **Full-text Search** | BM25 & analyzers |

### Operations Skills
| Skill | Description |
|-------|-------------|
| **Deployment** | Docker, Cloud, embedded |
| **Security** | Auth, RBAC, permissions |
| **Performance** | Indexing, optimization |
| **Monitoring** | Live queries, CDC |
| **Migrations** | SurrealKit, schema sync |

### Integration Skills
| Skill | Description |
|-------|-------------|
| **SDK Usage** | Python, JS, Go |
| **AI Integration** | OpenAI, LangChain |
| **MCP** | Model Context Protocol |
| **Custom Functions** | WASM extensions |

---

## 🔐 SECURITY COMPLIANCE

| Certification | Description |
|---------------|-------------|
| **SOC 2 Type 2** | Security & availability |
| **GDPR** | Data protection (EU) |
| **Cyber Essentials Plus** | UK security baseline |
| **ISO 27001** | Information security |

---

## 📋 QUICK REFERENCE

### Installation
```bash
# Linux
curl -sSf https://install.surrealdb.com | sh

# macOS
brew install surrealdb/tap/surreal

# Docker
docker run -p 8000:8000 surrealdb/surrealdb:latest start

# Python
pip install surrealdb
```

### Connection Strings
| Mode | URL |
|------|-----|
| In-memory | `mem://name` |
| RocksDB | `rocksdb:///path/file.db` |
| SurrealKV | `surrealkv:///path/file.db` |
| Distributed | `tikv://pd:2379` |
| WebSocket | `ws://host:port/rpc` |
| HTTP | `http://host:port` |

### Data Types
| Type | Example |
|------|---------|
| String | `'hello'` |
| Integer | `42` |
| Float | `3.14` |
| Boolean | `true` |
| Datetime | `time::now()` |
| Duration | `1h30m` |
| Array | `['a', 'b']` |
| Object | `{key: 'value'}` |
| Record | `user:alice` |
| Geometry | `(-0.12, 51.5)` |
| Vector | `[0.1, 0.2, 0.3]` |

---

## 🔗 RESOURCES

| Resource | URL |
|----------|-----|
| **Docs** | https://surrealdb.com/docs |
| **GitHub** | https://github.com/surrealdb/surrealdb |
| **Discord** | https://discord.gg/surrealdb |
| **X/Twitter** | @surrealdb |
| **YouTube** | SurrealDB |
| **LinkedIn** | surrealdb |
| **Blog** | https://surrealdb.com/blog |
| **Roadmap** | https://surrealdb.com/roadmap |