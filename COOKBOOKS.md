# Agent Memory Cookbooks

Real working examples from labs.surrealdb.com - copy, paste, run!

---

## 🍳 Quick Recipes (Under 5 min)

### Recipe 1: Hello World (30 sec)
```bash
# Start SurrealDB
docker run -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root memory

# Query
docker exec surrealdb surrealdb sql --user root --pass root -d agent
```
```sql
CREATE users SET name = 'Hello', world = 'SurrealDB!';
SELECT * FROM users;
```

### Recipe 2: Python CRUD (2 min)
```python
from surrealdb import Surreal

async def app():
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    # Create
    await db.query("CREATE article SET title = 'My First Post'")
    
    # Read
    articles = await db.query("SELECT * FROM article")
    print(articles)
```

---

## 🔌 SDK Connections

### Recipe 3: JavaScript SDK
```javascript
import { Surreal } from '@surrealdb/sdk'

const db = new Surreal()
await db.connect('ws://localhost:8000/rpc')
await db.use('memory:agent')
await db.signin({ username: 'root', password: 'root' })

const [article] = await db.query('SELECT * FROM article')
```

### Recipe 4: Go SDK
```go
import "github.com/surrealdb/golang"

db, _ := surreal.Dial("ws://localhost:8000/rpc")
db.Use("memory", "agent")
db.Signin("root", "root")
result := db.Query("SELECT * FROM article", nil)
```

### Recipe 5: Rust SDK
```rust
use surrealdb::Surreal;
use surrealdb::engine::local::Mem;

let db = Surreal::new::<Mem>(()).await?;
db.use_ns("memory").use_db("agent").await?;

let article: Option<Article> = db.create(("article", "one"))
    .content(Article { title: "My First Post".to_string() })
    .await?;
```

---

## 📊 Data Management

### Recipe 6: Phone Book CLI (Gabor Szabo)
```python
# pip install surrealdb
from surrealdb import Surreal

async def main():
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'phonebook'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    while True:
        name = input("Name: ")
        phone = input("Phone: ")
        await db.query("CREATE contact SET name = $name, phone = $phone", {"name": name, "phone": phone})
```

### Recipe 7: Schema in Surrealist
```sql
-- Design schema visually at http://localhost:3000
DEFINE TABLE person SCHEMAFULL;
DEFINE FIELD name ON person TYPE string;
DEFINE FIELD email ON person TYPE string ASSERT $value CONTAINS '@';
DEFINE FIELD phone ON person TYPE string;
```

---

## 🤖 AI & Vectors

### Recipe 8: Vector Store for LangChain
```python
from langchain_community.vectorstores import SurrealVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document

# Embeddings
embeddings = OpenAIEmbeddings()

# Store vectors
vectorstore = SurrealVectorStore.from_documents(
    documents=[Document(page_content="AI agents need memory", metadata={"source": "lab"})],
    embedding=embeddings,
    connection_string="ws://localhost:8000/rpc"
)

# Query
results = vectorstore.similarity_search("agent memory", k=3)
```

### Recipe 9: MCP Server (David Whatley)
```python
# surrealdb-mcp-server
pip install surrealdb-mcp-server

# Run
npx surrealdb-mcp-server ws://localhost:8000/rpc

# Use with Claude, GPT-4, etc
# Connect as MCP tool
```

### Recipe 10: Surreal-4o Fine-tuned Model
```python
# Create SurrealQL-structured data for fine-tuning
await db.query("""
    CREATE query SET 
        query_text = 'SELECT * FROM user',
        surreql = 'SELECT * FROM user',
        description = 'Get all users'
""")
```

---

## ⏰ Real-time

### Recipe 11: Live Queries (Presence)
```sql
-- Terminal 1: Subscribe
LIVE SELECT * FROM presence WHERE room = 'lobby';

-- Terminal 2: Add presence
CREATE presence SET user = 'alice', room = 'lobby', online = true;
```

### Recipe 12: Python Live Subscription
```python
async def subscribe():
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    
    async for change in db.listen():
        print(f"Change: {change}")
```

---

## 🔗 Graph Relations

### Recipe 13: Relate Users
```sql
-- Create users
CREATE user:alice SET name = 'Alice';
CREATE user:bob SET name = 'Bob';

-- Create relationship
RELATE user:alice -> follows -> user:bob;

-- Query
SELECT <-follows<-user.name FROM user:alice;
```

### Recipe 14: Nested Relations
```sql
-- Company -> Employee -> Project
CREATE company SET name = 'ACME';
CREATE employee SET name = 'Alice', company = company:acme;
CREATE project SET name = 'Login', team = employee:alice;

-- Traverse
SELECT company.name, employee.name, project.name 
FROM company:acme->employee->project;
```

---

## 🔍 Search

### Recipe 15: Full-Text Search
```sql
-- Create index
DEFINE INDEX search ON article FIELDS content SEARCH ANALYZER en BM25;

-- Search
SELECT * FROM article WHERE content @1@ 'search term';
```

### Recipe 16: Hybrid Search
```sql
LET $text = SELECT * FROM doc WHERE content @1@ 'question';
LET $vec = SELECT * FROM doc WHERE embedding <|5|> $query;
SELECT * FROM search::rrf([$text, $vec], 5, 60);
```

---

## 🏗️ Full Stack

### Recipe 17: Vue Blog Starter (Fadel SrWither)
```bash
# Clone
git clone https://github.com/FadelSrWither/surrealdb-vue-blog.git
cd surrealdb-vue-blog
npm install

# Run
npm run dev
```

### Recipe 18: SvelteKit Auth (Jonathan Gamble)
```bash
# Clone
git clone https://github.com/jonathan-gamble/sveltekit-surreal-auth
cd sveltekit-surreal-auth
npm install

# Configure .env
SURREAL_USER=root
SURREAL_PASS=root
SURREAL_NS=memory
SURREAL_DB=auth
```

### Recipe 19: Go Starter (Salman Shah)
```go
package main

import (
    "github.com/surrealdb/golang"
)

func main() {
    db, _ := surreal.Dial("ws://localhost:8000/rpc")
    db.Use("memory", "app")
    db.Signin("root", "root")
}
```

---

## 🔧 DevOps

### Recipe 20: GitHub Action
```yaml
# .github/workflows/test.yml
- name: SurrealDB
  uses: surrealdb/github-action@v1
  with:
    args: start --user root --pass root memory
- run: npm test
```

### Recipe 21: Grafana Datasource
```yaml
# docker-compose.yml
grafana:
  image: grafana/grafana
# Add datasource: ws://surrealdb:8000/rpc
```

### Recipe 22: Terraform GKE (Dylan Vanmali)
```hcl
module "surrealdb" {
  source = "github.com/dylan-vanmali/terraform-gke-surrealdb"
}
```

---

## 🎓 Learning

### Recipe 23: Live Stream Series (Xkonti)
```bash
# Watch SurrealDB in action
# https://www.youtube.com/@Xkonti
```

### Recipe 24: Rust Embedded (Jeremy Chone)
```rust
use surrealdb::engine::local::Mem;

let db = Surreal::new::<Mem>(()).await?;
let created: Option<User> = db
    .create(("user", "me"))
    .content(User { name: "Me".into() })
    .await?;
```

---

## 📦 Templates

### Recipe 25: Gin/Gonic API (Atharva Deshpande)
```go
import (
    "github.com/gin-gonic/gin"
    "github.com/surrealdb/golang"
)

func main() {
    r := gin.Default()
    db, _ := surreal.Dial("ws://localhost:8000/rpc")
    
    r.GET("/users", func(c *gin.Context) {
        users, _ := db.Query("SELECT * FROM user", nil)
        c.JSON(200, users)
    })
    
    r.Run(":8080")
}
```

### Recipe 26: Fresh Deno (Rajdeep Singh)
```typescript
// deno.json
{
  "imports": {
    "surrealdb": "https://esm.surreal.team/surreal@3.0.5"
  }
}

// main.ts
import { Surreal } from 'surrealdb'
const db = new Surreal()
await db.connect('mem://test')
```

---

## 🛡️ Security

### Recipe 27: User Groups (Official)
```sql
DEFINE USER alice ON DATABASE PASSWORD 'pass123';
DEFINE ROLE admin PERMISSIONS FULL;
DEFINE ROLE user PERMISSIONS SELECT;

GRANT admin TO alice;
```

### Recipe 28: Multi-Tenant RBAC (Sebastian Wessel)
```sql
DEFINE TABLE tenant SCHEMAFULL;
DEFINE FIELD name ON tenant TYPE string;

DEFINE TABLE project PERMISSIONS 
    SELECT WHERE tenant = $auth.tenant
    CREATE WHERE tenant = $auth.tenant;
```

---

## ☁️ Cloud

### Recipe 29: SurrealDB Cloud
```python
# Connect to cloud
db = Surreal('wss://cloud.surrealdb.com/rpc')
await db.connect()
await db.signin({
    'namespace': 'my-ns',
    'database': 'my-db',
    'username': 'root',
    'password': 'password'
})
```

---

## 🧪 Try These

| # | Recipe | Time | Difficulty |
|-----|-------|------|-----------|
| 1 | Hello World | 30s | 🟢 |
| 2 | Python CRUD | 2min | 🟢 |
| 3 | JS SDK | 2min | 🟢 |
| 4 | Graph Relations | 3min | 🟡 |
| 5 | Vector Search | 5min | 🟡 |
| 6 | LIVE Queries | 3min | 🟡 |
| 7 | Full-Text Search | 3min | 🟡 |
| 8 | LangChain | 5min | 🟠 |
| 9 | Full Stack | 10min | 🟠 |