# SurrealDB Python SDK Skill

## Installation

```bash
pip install surrealdb
```

## Connection

### Client Mode (WebSocket)
```python
from surrealdb import Surreal

db = Surreal('ws://localhost:8000/rpc')
await db.connect()
await db.use({'namespace': 'memory', 'database': 'agent'})
await db.signin({'username': 'root', 'password': 'root'})
```

### Embedded Mode
```python
from surrealdb import Surreal

db = Surreal('mem://')
await db.connect()
await db.use({'namespace': 'memory', 'database': 'agent'})
```

## CRUD Operations

### Create
```python
await db.query("CREATE user SET name = $name", {"name": "Alice"})
result = await db.query("CREATE user SET name = 'Bob'")
```

### Read
```python
users = await db.query("SELECT * FROM user")
users = await db.query("SELECT * FROM user WHERE role = $role", {"role": "admin"})
```

### Update
```python
await db.query("UPDATE user:alice SET name = 'Alice' WHERE id = user:alice")
```

### Delete
```python
await db.query("DELETE FROM user WHERE id = user:alice")
```

## Graph Operations
```python
await db.query("RELATE user:alice -> follows -> user:bob")
results = await db.query("SELECT * FROM user:alice->follows->user")
```

## Live Queries
```python
async for change in db.listen():
    print(f"Change: {change}")
```

## Transactions
```python
async with db.transaction():
    await db.query("CREATE order SET user = $user", ...)
    await db.query("UPDATE user SET orders += $order", ...)
```

## Resources
- [Python SDK Docs](https://surrealdb.com/docs/surrealql/sdk/python)