# Agent Memory - Actionable Demos

Run these to actually USE SurrealDB.

---

## Quick Demo (30 seconds)

```bash
# 1. Start container
docker run -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root memory

# 2. In another terminal - query
docker exec -it surrealdb surrealdb sql --user root --pass root --db agent
```

```sql
-- Try these
CREATE user SET name = 'Alice', role = 'admin';
SELECT * FROM user;
UPDATE user SET role = 'superadmin';
DELETE FROM user;
```

---

## Python Demo (2 min)

```python
# pip install surrealdb openai
from surrealdb import Surreal

async def demo():
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    # Create
    await db.query("CREATE user SET name = 'Alice'")
    
    # Read
    result = await db.query("SELECT * FROM user")
    print(result)
    
    await db.close()

# Run: python demo.py
```

---

## Vector Search Demo (3 min)

```python
from surrealdb import Surreal
from openai import AsyncOpenAI
import numpy as np

async def vector_demo():
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    llm = AsyncOpenAI()
    
    # Generate embedding
    response = await llm.embeddings.create(
        model="text-embedding-3-small",
        input="AI agent memory"
    )
    emb = response.data[0].embedding
    
    # Store in DB
    await db.query(
        "CREATE article SET title = 'Agent Memory', embedding = $emb",
        {"emb": emb}
    )
    
    # Search
    query_emb = (await llm.embeddings.create(
        model="text-embedding-3-small", 
        input="memory for agents"
    )).data[0].embedding
    
    results = await db.query(
        """SELECT *, vector::distance::knn() AS score 
        FROM article WHERE embedding <|5|> $q""",
        {"q": query_emb}
    )
    
    print(results)

# Run: python vector_demo.py
```

---

## Agent Memory Demo (5 min)

```python
from surrealdb import Surreal
import uuid

async def agent_memory_demo():
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    session_id = f"session:{uuid.uuid4().hex[:8]}"
    
    # 1. Create session
    await db.query(f"""
        CREATE {session_id} SET 
        user_id = 'user:1',
        status = 'active'
    """)
    
    # 2. Add entities
    await db.query("""
        CREATE entity SET 
        session = $sess, 
        type = 'person', 
        name = 'Alice',
        properties = {email: 'alice@test.com'}
    """, {"sess": session_id})
    
    # 3. Trace decision
    await db.query("""
        CREATE decision SET 
        session = $sess,
        action = 'search',
        tool = 'article',
        result = 'Found 3 articles'
    """, {"sess": session_id})
    
    # 4. Get full context
    context = await db.query(f"""
        SELECT 
            (SELECT * FROM entity WHERE session = $sess) AS entities,
            (SELECT * FROM decision WHERE session = $sess) AS decisions
        FROM {session_id}
    """, {"sess": session_id})
    
    print(context)

# Run: python agent_memory_demo.py
```

---

## Graph Visualization Demo (3 min)

```bash
# Start Surrealist UI
docker run -p 3000:3000 -e SURREAL_DB_URL=ws://surrealdb:8000/rpc surrealdb/surrealist:latest
```

Then open http://localhost:3000

---

## LIVE Query Demo (2 min)

```sql
-- Terminal 1: Subscribe
LIVE SELECT * FROM message WHERE session = 'session:1';

-- Terminal 2: Add message
CREATE message SET session = 'session:1', content = 'Hello';
```

Watch it appear in Terminal 1!

---

## Hybrid RAG Demo (5 min)

```python
from surrealdb import Surreal
from openai import AsyncOpenAI

async def hybrid_rag():
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    llm = AsyncOpenAI()
    query = "how to reset password"
    
    # Get query embedding
    q_emb = (await llm.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )).data[0].embedding
    
    # Hybrid search
    results = await db.query("""
        LET $q = $query;
        LET $emb = $embedding;
        
        -- Vector search
        LET $vs = SELECT id, title, 
            vector::similarity::cosine(embedding, $emb) AS vs
        FROM article WHERE embedding <|10|> $emb;
        
        -- Text search  
        LET $ft = SELECT id, title, search::score(1) AS ts
        FROM article WHERE content @1@ $q;
        
        -- Combine
        SELECT * FROM search::rrf([$vs, $ft], 5, 60)
        LIMIT 5;
    """, {"query": query, "embedding": q_emb})
    
    print(results)

# Run: python hybrid_rag.py
```

---

## Docker Compose Up (1 min)

```bash
# Start everything
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Open Surrealist
# http://localhost:3000

# Query from CLI
docker exec -it agent-memory-db-1 surrealdb sql --user root --pass root
```

---

## Run Tests (2 min)

```bash
# Run SurrealKit tests
docker-compose --profile dev up -d surrealkit
docker exec agent-memory-kit surrealkit test

# Or manually
surrealkit sync   # Sync schema
surrealkit seed  # Seed data  
surrealkit test  # Run tests
```

---

## Install & Run (30 sec)

```bash
# macOS
brew install surrealdb/tap/surreal
surreal start --user root --pass root memory

# Linux
curl -sSf https://install.surrealdb.com | sh

# Python
pip install surrealdb openai
```

---

## What To Build Next

| Project | Time | Description |
|--------|------|-------------|
| 1. CRUD API | 10 min | REST API with FastAPI |
| 2. Chat Memory | 15 min | Chat with session memory |
| 3. RAG Pipeline | 20 min | Hybrid search with LLM |
| 4. Agent | 30 min | Tool-using agent |
| 5. Dashboard | 30 min | Surrealist + charts |