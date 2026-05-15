# Skill: SurrealDB Administration

Administer SurrealDB: users, permissions, indexes, monitoring.

## Users & Auth

```sql
-- Create user
DEFINE USER alice ON DATABASE PASSWORD 'secure123';

-- Create role
DEFINE ROLE admin PERMISSIONS FULL;
DEFINE ROLE viewer PERMISSIONS SELECT;

-- Grant role
GRANT admin TO alice;

-- Sign in
SIGNIN DATABASE USER alice PASSHASH $hash;
```

## Indexes

```sql
-- Unique
DEFINE INDEX email ON user COLUMNS email UNIQUE;

-- Compound
DEFINE INDEX session_user ON session COLUMNS user_id, created;

-- Full-text
DEFINE INDEX search ON article FIELDS content SEARCH BM25;

-- Vector (HNSW)
DEFINE INDEX vec ON article FIELDS embedding HNSW DIMENSION 512;
```

## Schema

```sql
-- Define table
DEFINE TABLE user TYPE ANY SCHEMAFULL;

-- Define field with constraints
DEFINE FIELD name ON user TYPE string ASSERT $value IS NOT NULL;
DEFINE FIELD email ON user TYPE string ASSERT $value CONTAINS '@';

-- Events
DEFINE EVENT ON user WHEN $event = 'CREATE' THEN (
    CREATE log SET action = 'user_created', data = $this
);
```

## Migration

```bash
# Install surrealkit
pip install surrealkit

# Sync schema
surrealkit sync

# Run tests
surrealkit test
```

## Monitoring

```sql
-- LIVE query
LIVE SELECT * FROM log;

-- Health check
SELECT * FROM _health;

-- Connections
SELECT * FROM _connections;
```

## Backup

```bash
# Export
surreal export --ns memory --db agent --exp /data/export.surql

# Import
surreal import --ns memory --db agent --imp /data/export.surql
```

## Resources

- [Docs](https://surrealdb.com/docs)
- [Security](https://surrealdb.com/docs/security)