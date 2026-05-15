# Skill: Vector Search

Implement vector similarity search for AI/RAG applications.

## Store Embeddings

```sql
-- Store a document with embedding
CREATE article SET 
    title = 'RAG Guide',
    content = 'Retrieval-augmented generation...',
    embedding = [0.1, 0.2, 0.3, 0.4, 0.5];
```

## Create Vector Index

```sql
-- HNSW index (recommended)
DEFINE INDEX vec_idx ON article 
FIELDS embedding 
HNSW DIMENSION 512 
DIST COSINE;
```

## Similarity Search

```sql
-- K-nearest neighbors
LET $query = [0.1, 0.2, 0.3, 0.4, 0.5];
SELECT 
    id, 
    title,
    vector::distance::knn() AS distance
FROM article 
WHERE embedding <|5|> $query
ORDER BY distance ASC;
```

## Distance Metrics

| Metric | Best For |
|--------|---------|
| COSINE | General (angle between vectors) |
| EUCLIDEAN | Exact match |
| MANHATTAN | Grid-based |

## Hybrid Search

```sql
-- Text results
LET $text = SELECT id, search::score(1) AS s 
FROM article WHERE content @1@ 'query';

-- Vector results
LET $vec = SELECT id, vector::distance::knn() AS d 
FROM article WHERE embedding <|10|> $query;

-- Combine
SELECT search::rrf([$text, $vec], 5, 60);
```

## Embeddings with OpenAI

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()
response = await client.embeddings.create(
    model="text-embedding-3-small",
    input="Your text here"
)
embedding = response.data[0].embedding

# Store in SurrealDB
await db.query(
    "CREATE article:$id SET embedding = $embedding;",
    {"id": "article:1", "embedding": embedding}
)
```

## RAG Pipeline

```python
async def rag_query(query: str, top_k: int = 5):
    # 1. Get query embedding
    emb = await get_embedding(query)
    
    # 2. Search SurrealDB
    results = await db.query(
        """SELECT *, vector::distance::knn() AS score
        FROM article WHERE embedding <|$k|> $emb
        ORDER BY score LIMIT $k;""",
        {"k": top_k, "emb": emb}
    )
    
    # 3. Build context
    context = "\n\n".join([r['content'] for r in results[0]])
    
    # 4. Call LLM
    response = await llm.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": f"Context: {context}"},
            {"role": "user", "content": query}
        ]
    )
    
    return response.choices[0].message.content
```

## Resources

- [Docs](https://surrealdb.com/docs)
- [Vector Search](https://surrealdb.com/docs/surrealql/search)