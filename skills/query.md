# Skill: SurrealDB Query

Master SurrealQL for querying SurrealDB.

## Quick Start

```sql
-- Basic queries
SELECT * FROM user;
CREATE user SET name = 'Alice';
UPDATE user:alice SET role = 'admin';
DELETE FROM user WHERE role = 'guest';
```

## Select

```sql
-- Filter
SELECT * FROM session WHERE status = 'active';

-- Specific fields
SELECT id, name, email FROM user;

-- Order & limit
SELECT * FROM article ORDER BY created DESC LIMIT 10;

-- Nested
SELECT profile.bio FROM user;

-- Graph traversal
SELECT <-authored<-article FROM user:alice;
```

## Create

```sql
-- Basic
CREATE user SET name = 'Alice', role = 'admin';

-- With ID
CREATE user:alice SET name = 'Alice';

-- Nested
CREATE article SET 
    title = 'Guide',
    content = '...',
    tags = ['tutorial', 'guide'];
```

## Update

```sql
-- Single
UPDATE user:alice SET role = 'admin';

-- Multiple
UPDATE user:alice SET role = 'admin', status = 'active';

-- Increment
UPDATE article SET views = views + 1;

-- Conditional
UPDATE session SET status = 'completed' WHERE status = 'active';
```

## Delete

```sql
DELETE FROM user WHERE id = 'user:alice';
DELETE FROM session WHERE created < time::now() - 30d;
```

## Functions

```sql
-- String
SELECT string::upper('hello');  -- HELLO
SELECT string::len('hello');     -- 5

-- Math
SELECT math::round(3.7);       -- 4
SELECT math::sqrt(16);         -- 4

-- Time
SELECT time::now();
SELECT time::format(time::now(), '%Y-%m-%d');
```

## Resources

- [Docs](https://surrealdb.com/docs/surrealql)
- [Sample Queries](https://surrealdb.com/docs/sample-queries)