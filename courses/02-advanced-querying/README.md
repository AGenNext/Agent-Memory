# Course: Advanced Querying
# LIVE Queries, Full-Text, Vectors

## Overview

This course covers advanced SurrealQL features: LIVE queries, full-text search, and vector similarity.

**Duration:** 3 hours  
**Level:** Intermediate  
**Prerequisites:** Course 1 - Querying Fundamentals

---

## Learning Objectives

- [ ] Use LIVE queries for real-time data
- [ ] Implement full-text search
- [ ] Perform vector similarity search
- [ ] Combine text + vectors with hybrid search

---

## Lesson 2.1: LIVE Queries

LIVE queries subscribe to data changes in real-time.

### Concept

Instead of polling, subscribe to changes:

```sql
-- Subscribe to new sessions
LIVE SELECT * FROM session;
```

### Creating a LIVE Query

```sql
-- Monitor active sessions
LIVE SELECT * FROM session WHERE status = 'active';
```

### LIVE Query Response

When data changes, you receive notifications:

```json
{
    "action": "CREATE",
    "record": {
        "id": "session:new123",
        "status": "active"
    }
}
```

### Example 1: Monitor Messages

```sql
-- Watch for new messages
LIVE SELECT * FROM message WHERE session = 'session:1';
```

### Example 2: Monitor Decisions

```sql
-- Watch all decisions
LIVE SELECT * FROM decision;
```

### Example 3: Filtered Live Query

```sql
-- Only high priority tickets
LIVE SELECT * FROM ticket WHERE priority = 'high';
```

### Killing LIVE Queries

```sql
-- Get query ID from LIVE response
LIVE SELECT * FROM session;

-- Kill specific query
KILL "query_id_here";

-- Kill all
KILL ALL;
```

### Exercise 1

1. Create a LIVE query for new sessions
2. Create a LIVE query for decision changes
3. Kill a query

---

## Lesson 2.2: Full-Text Search

Full-text search finds text matching keywords.

### Creating Index

```sql
-- Create analyzer
DEFINE ANALYZER simple TOKENIZERS blank FILTERS lowercase;

-- Create full-text index
DEFINE INDEX search_idx ON article 
FIELDS content 
SEARCH ANALYZER simple BM25;
```

### Searching

```sql
-- Basic search (match any)
SELECT * FROM article WHERE content @1@ 'authentication';

-- Match all terms
SELECT * FROM article WHERE content @ 'agent memory';

-- With relevance score
SELECT *, search::score(1) AS score 
FROM article 
WHERE content @1@ 'agent' 
ORDER BY score DESC;
```

### Multiple Terms

```sql
-- One term matches
SELECT * FROM article WHERE content @1@ 'authentication';

-- Two terms
SELECT * FROM article WHERE content @2@ 'authentication login';

-- All terms
SELECT * FROM article WHERE content @ 'authentication login reset';
```

### Highlights

```sql
-- Get highlighted matches
SELECT 
    id,
    search::highlight('<b>', '</b>', 1) AS title,
    search::highlight('<em>', '</em>', 1) AS content
FROM article 
WHERE content @1@ 'agent';
```

### Exercise 2

1. Create a full-text index on article content
2. Search for 'agent' in articles
3. Get results with scores

---

## Lesson 2.3: Vector Similarity

Vectors enable semantic similarity search.

### Creating Embeddings

```sql
-- Store embedding
CREATE article:intro SET 
    title = 'Agent Memory Guide',
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5];
```

### Vector Index

```sql
-- HNSW index (recommended)
DEFINE INDEX vec_idx ON article 
FIELDS embedding 
HNSW DIMENSION 512 
DIST COSINE;
```

### Similarity Search

```sql
-- Query vector
LET $query = [0.1, 0.2, 0.3, 0.4, 0.5];

-- Find similar (k nearest)
SELECT 
    id, 
    title,
    vector::distance::knn() AS distance
FROM article 
WHERE embedding <|5|> $query
ORDER BY distance ASC;
```

### Distance Metrics

| Metric | Best For | Description |
|--------|----------|-------------|
| `COSINE` | General | Angle between vectors |
| `EUCLIDEAN` | Exact match | Straight-line distance |
| `MANHATTAN` | Grid-based | Sum of differences |

### Exercise 3

1. Add embeddings to articles
2. Create vector index
3. Search for similar articles

---

## Lesson 2.4: Hybrid Search

Combine text + vector for best results.

### Reciprocal Rank Fusion

```sql
-- Text search results
LET $text = (
    SELECT id, search::score(1) AS score 
    FROM article 
    WHERE content @1@ 'agent memory'
    ORDER BY score DESC 
    LIMIT 10
);

-- Vector search results
LET $vec = (
    SELECT id, vector::distance::knn() AS dist 
    FROM article 
    WHERE embedding <|10|> $query
);

-- Combine with RRF
SELECT search::rrf([$text, $vec], 5, 60);
```

### RRF Formula

```
RRF(d) = Σ 1/(k + rank(d))
```

- `k` = constant (usually 60)
- `rank(d)` = position in results

### Exercise 4

1. Run text search
2. Run vector search
3. Combine with RRF

---

## Summary

| Feature | Use Case |
|---------|----------|
| LIVE | Real-time subscriptions |
| FULLTEXT | Keyword search |
| VECTOR | Semantic similarity |
| HYBRID | Best of both |

### Next Course

[Course 3: Data Models →](../03-data-models/README.md)