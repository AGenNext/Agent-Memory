# SurrealQL - Query Language Skill

## Overview
SurrealQL is SurrealDB's query language. It combines SQL-like syntax with graph, document, vector, and time-series capabilities.

## Basic Syntax

### Select
```sql
SELECT * FROM user;
SELECT name, email FROM user WHERE role = 'admin';
SELECT * FROM user ORDER BY created_at DESC LIMIT 10;
```

### Create
```sql
CREATE user SET name = 'Alice', email = 'alice@test.com';
CREATE user:alice SET name = 'Alice';
```

### Update
```sql
UPDATE user SET name = 'Bob' WHERE email = 'bob@test.com';
UPDATE user:alice SET name = 'Alice', role = 'admin';
```

### Delete
```sql
DELETE FROM user WHERE id = user:alice;
DELETE FROM user WHERE age < 18;
```

## Schema

### Define Table
```sql
DEFINE TABLE user SCHEMAFULL;
DEFINE TABLE user SCHEMALESS;

DEFINE FIELD name ON user TYPE string;
DEFINE FIELD email ON user TYPE string ASSERT $value CONTAINS '@';
DEFINE FIELD age ON user TYPE int DEFAULT 18;
DEFINE FIELD tags ON user TYPE array<string>;
```

### Define Index
```sql
DEFINE INDEX user_email ON user FIELDS email UNIQUE;
DEFINE INDEX user_name ON user FIELDS name SEARCH ANALYZER en BM25;
DEFINE INDEX vec ON doc FIELDS embedding HNSW DIMENSION 1536 DISTANCE COSINE;
```

## Graph

### Relationships
```sql
RELATE user:alice -> follows -> user:bob;
RELATE user:alice -> wrote -> article:1 SET at = time::now();
```

### Traversal
```sql
SELECT * FROM user:alice->follows->user;
SELECT <-follows<-user FROM user:bob;
SELECT * FROM user:alice->wrote->article WHERE published = true;
```

## Parameters

### Use Parameters
```sql
LET $name = 'Alice';
SELECT * FROM user WHERE name = $name;
SELECT * FROM user WHERE name CONTAINS $search;
```

## More

- Live queries: `LIVE SELECT * FROM table`
- Transactions: `BEGIN TRANSACTION; ... COMMIT;`
- Functions: `DEFINE FUNCTION fn::name ...`
- Events: `DEFINEEVENT ON table ...`

## Resources
- [SurrealQL Reference](https://surrealdb.com/docs/surrealql)