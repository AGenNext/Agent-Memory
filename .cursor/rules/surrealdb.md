# SurrealDB Agent Rules

Based on: https://surrealdb.com/docs/build/ai-agents/agent-rules

## SurrealQL Conventions

### Schema
- Use `SCHEMAFULL` for strict schema, `SCHEMALESS` for flexible
- Define fields with types: `string`, `int`, `float`, `bool`, `datetime`, `array`, `object`
- Use `ASSERT` for validation

### Queries
- Always use parameterized queries: `WHERE field = $value`
- Use `SELECT * FROM table` not `SELECT * table`
- Graph traversal: `<-relates<-entity`

### Relationships
- Use `RELATE entity:a -> relates -> entity:b`
- Type relations: `DEFINE TABLE relates TYPE RELATION FROM entity TO entity`

---

## Vector Search

### Index
```sql
DEFINE INDEX vec_idx ON doc FIELDS embedding HNSW DIMENSION 512 DISTANCE COSINE;
```

### Query
```sql
SELECT *, vector::distance::knn() AS dist FROM doc WHERE embedding <|5|> $query;
```

### Hybrid
```sql
LET $text = SELECT * FROM doc WHERE content @1@ $query;
LET $vec = SELECT * FROM doc WHERE embedding <|5|> $embedding;
SELECT * FROM search::rrf([$text, $vec], 5, 60);
```

---

## Python SDK

### Connect
```python
from surrealdb import Surreal

db = Surreal('ws://localhost:8000/rpc')
await db.connect()
await db.use({'namespace': 'memory', 'database': 'agent'})
await db.signin({'username': 'root', 'password': 'root'})
```

### CRUD
```python
await db.query("CREATE user SET name = $name", {"name": "Alice"})
await db.query("SELECT * FROM user")
await db.query("UPDATE user SET name = $name WHERE id = $id", ...)
await db.query("DELETE FROM user WHERE id = $id")
```

### Live Queries
```python
async for change in db.listen():
    print(change)
```

---

## Best Practices

1. Use parameterized queries to prevent injection
2. Define indexes for search fields
3. Use transactions for multi-table writes
4. Use live queries for real-time updates
5. Store embeddings as array[float]