# SurrealDB JavaScript SDK Skill

## Installation

```bash
npm install @surrealdb/sdk
```

## Connection

### WebSocket
```javascript
import { Surreal } from '@surrealdb/sdk'

const db = new Surreal()
await db.connect('ws://localhost:8000/rpc')
await db.use('memory:agent')
await db.signin({ username: 'root', password: 'root' })
```

### In-Memory
```javascript
await db.connect('mem://')
```

## CRUD Operations

### Create
```javascript
await db.query('CREATE user SET name = $name', { name: 'Alice' })
const [user] = await db.query('CREATE user SET name = "Bob"')
```

### Read
```javascript
const users = await db.query('SELECT * FROM user')
const admins = await db.query('SELECT * FROM user WHERE role = $role', { role: 'admin' })
```

### Update
```javascript
await db.query('UPDATE user:alice SET name = "Alice"')
```

### Delete
```javascript
await db.query('DELETE FROM user WHERE id = user:alice')
```

## Graph Operations
```javascript
await db.query('RELATE user:alice -> follows -> user:bob')
const follows = await db.query('SELECT * FROM user:alice->follows->user')
```

## Live Queries
```javascript
const live = await db.query('LIVE SELECT * FROM user')
for await (const change of live) {
  console.log('Change:', change)
}
```

## Node.js
```javascript
import { Surreal } from '@surrealdb/node'

const db = new Surreal()
await db.connect('ws://localhost:8000/rpc')
```

## TypeScript
```typescript
import { Surreal } from '@surrealdb/sdk'

interface User {
  id: string
  name: string
  email: string
}

const db = new Surreal()
await db.connect('ws://localhost:8000/rpc')

const [user] = await db.query<User>('SELECT * FROM user LIMIT 1')
```

## Resources
- [JS SDK Docs](https://surrealdb.com/docs/surrealql/sdk/javascript)