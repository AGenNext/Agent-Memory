# Skill: Data Models

Work with SurrealDB's multi-model data: documents, graphs, vectors, time-series.

## Documents

```sql
-- Nested objects
CREATE user SET 
    name = 'Alice',
    profile = {
        bio: 'Developer',
        address: { city: 'NYC', country: 'USA' },
        social: ['twitter', 'github']
    };
```

## Graph

```sql
-- Create relationship
RELATE user:alice -> wrote -> article:intro;

-- With properties
RELATE user:alice -> rated -> article:intro SET rating = 5;

-- Traverse
SELECT <-wrote<-article FROM user:alice;
SELECT ->wrote->article-><-references<-product FROM user:alice;
```

## Vectors

```sql
-- Store embedding
CREATE article SET 
    title = 'Guide',
    embedding = [0.1, 0.2, 0.3];

-- Search
SELECT *, vector::distance::knn() FROM article 
WHERE embedding <|5|> $query;

-- Hybrid (text + vector)
SELECT search::rrf([$text, $vector], 5, 60);
```

## Time-Series

```sql
-- Create sensor reading
CREATE sensor SET 
    value = 22.5,
    location = 'warehouse-1',
    recorded = time::now();

-- Query range
SELECT * FROM sensor WHERE recorded > d'2025-01-01';

-- Aggregate by time
SELECT time::format(recorded, '%Y-%m') AS month, math::avg(value) 
FROM sensor GROUP BY month;
```

## Full-Text

```sql
-- Search
SELECT * FROM article WHERE content @1@ 'agent memory';

-- With score
SELECT *, search::score(1) AS score FROM article 
WHERE content @1@ 'search' ORDER BY score DESC;
```

## Resources

- [Docs](https://surrealdb.com/docs)
- [Data Types](https://surrealdb.com/docs/surrealql/types)