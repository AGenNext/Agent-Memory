# Agent Memory - Learning Guide

Based on SurrealDB documentation: https://surrealdb.com/docs

## Learn Path

### 1. Getting Started
- [Understanding SurrealDB](https://surrealdb.com/docs) - Core concepts
- [Architecture](https://surrealdb.com/docs) - How SurrealDB works
- [Sample Queries](https://surrealdb.com/docs/sample-queries) - Basic SurrealQL

**Quick Start:**
```bash
# Start SurrealDB
surreal start --user root --pass root memory

# Open SQL REPL
surreal sql
```

### 2. Installation
Choose your platform:

| Platform | Install Command |
|----------|----------------|
| **Linux** | `curl -sSf https://install.surrealdb.com \| sh` |
| **macOS** | `brew install surrealdb/tap/surreal` |
| **Windows** | `iwr https://windows.surrealdb.com -useb \| iex` |
| **Docker** | `docker run -p 8000:8000 surrealdb/surrealdb:latest start` |

### 3. Storage Modes
- [In-memory](https://surrealdb.com/docs/self-hosted/in-memory) - Fast, no persistence
- [File-backed](https://surrealdb.com/docs/self-hosted/file-backed) - RocksDB or SurrealKV
- [Multi-node](https://surrealdb.com/docs/self-hosted/multi-node) - Distributed with TiKV

### 4. Data Models
- [Documents](https://surrealdb.com/docs) - Flexible nested JSON
- [Graph](https://surrealdb.com/docs) - Relationships via record links
- [Vectors](https://surrealdb.com/docs) - Embeddings for AI
- [Time-series](https://surrealdb.com/docs) - Temporal data

### 5. Query Language (SurrealQL)
- [SELECT](sample-queries) - Reading data
- [CREATE](sample-queries) - Insert records
- [UPDATE](sample-queries) - Modify records
- [RELATE](sample-queries) - Graph edges
- [LIVE](sample-queries) - Real-time queries
- [FULLTEXT](sample-queries) - Search
- [Vectors](sample-queries) - Similarity search

### 6. Schema
Def tables, fields, indexes, events, functions.

### 7. Security
- Authentication (user/pass, JWT)
- RBAC with roles
- Record-level permissions
- Scoped access

### 8. Agent Memory
- [Spectron](https://surrealdb.com/platform/spectron) - Built-in memory
- Entity extraction
- Knowledge graphs
- Hybrid retrieval

### 9. Extensions
- [WASM plugins](https://surrealdb.com/platform/surrealdb/extensibility) - Custom logic
- SurrealML - In-database ML inference

### 10. Tools
- [Surrealist](https://surrealdb.com/surrealist) - Visual IDE
- [SurrealKit](https://github.com/surrealdb/surrealkit) - Migrations & testing

## Hands-On Tutorials

### Tutorial 1: Basic CRUD
```surrealql
CREATE user:alice SET name = 'Alice', role = 'admin';
SELECT * FROM user WHERE name = 'Alice';
UPDATE user:alice SET role = 'user';
DELETE user:alice;
```

### Tutorial 2: Graph Relationships
```surrealql
CREATE article:intro SET title = 'Getting Started';
CREATE product:auth SET name = 'Auth Service';
RELATE article:intro -> references -> product:auth;
SELECT <-references<-article FROM product:auth;
```

### Tutorial 3: Vector Search
```surrealql
CREATE article SET embedding = [0.1, 0.2, 0.3];
LET $query = [0.1, 0.2, 0.3];
SELECT id, vector::distance::knn() FROM article WHERE embedding <|5|> $query;
```

### Tutorial 4: Full-Text Search
```surrealql
CREATE article SET content = 'Agent memory enables persistent context';
SELECT * FROM article WHERE content @1@ 'agent memory';
```

### Tutorial 5: Live Queries
```surrealql
LIVE SELECT * FROM session WHERE status = 'active';
-- New sessions appear automatically
```

### Tutorial 6: Functions
```surrealql
DEFINE FUNCTION fn::greet($name) [
    RETURN 'Hello, ' + $name + '!'
];
SELECT fn::greet('World');
```

## Common Patterns

### Pattern 1: Session with Entities
```surrealql
-- Create session
CREATE session SET user_id = 'user:1', status = 'active';

-- Add entities
CREATE entity SET session = 'session:1', type = 'person', name = 'Alice';

-- Trace decision
CREATE decision SET session = 'session:1', action = 'search';
```

### Pattern 2: Article → Product → Solution
```surrealql
CREATE article SET title = 'Guide', content = '...';
CREATE product SET name = 'Auth';
CREATE solution SET title = 'Fix';

RELATE article -> references -> product;
RELATE ticket -> about -> product;
RELATE ticket -> resolved_by -> solution;
```

### Pattern 3: Real-time Feed
```surrealql
LIVE SELECT * FROM message WHERE session = 'session:1';
-- Auto-updates
```

### Pattern 4: Access Control
```surrealql
DEFINE USER alice ON DATABASE PASSWORD 'pass123';
DEFINE SCOPE api READONLY;
GRANT api ON DATABASE TO alice;
```

## SDK Quick Reference

### Python
```python
from surrealdb import Surreal

db = Surreal('ws://localhost:8000/rpc')
await db.connect()
await db.use({'namespace': 'memory', 'database': 'agent'})
await db.signin({'username': 'root', 'password': 'root'})
result = await db.query('SELECT * FROM session')
```

### JavaScript
```javascript
import { Surreal } from '@surrealdb/sdk'

const db = new Surreal()
await db.connect('ws://localhost:8000/rpc')
await db.use('memory:agent')
await db.signin({ username: 'root', password: 'root' })
const [sessions] = await db.query('SELECT * FROM session')
```

### Go
```go
import "github.com/surrealdb/golang"

db, _ := surreal.Dial("ws://localhost:8000/rpc")
db.Use("memory", "agent")
db.Signin("root", "root")
surreal.Query("SELECT * FROM session", nil)
```

## Resources

| Resource | URL |
|---------|-----|
| **Docs** | https://surrealdb.com/docs |
| **Surrealist** | https://surrealdb.com/surrealist |
| **GitHub** | https://github.com/surrealdb/surrealdb |
| **Discord** | https://discord.gg/surrealdb |
| **Spectron** | https://surrealdb.com/platform/spectron |
| **SurrealKV** | https://github.com/surrealdb/surrealkv |
| **SurrealKit** | https://github.com/surrealdb/surrealkit |