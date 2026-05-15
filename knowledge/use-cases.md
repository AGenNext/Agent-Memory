# Use Cases

## Industries

### Financial Services
- Real-time fraud detection
- Trading platforms
- Risk management
- Customer 360

### Healthcare
- Patient records
- Medical imaging
- Drug discovery
- Telemedicine

### Retail & E-commerce
- Product catalogs
- Inventory management
- Customer personalization
- Supply chain

### Gaming
- Player profiles
- Leaderboards
- Matchmaking
- Economy management

### AI & Machine Learning
- Vector storage
- RAG pipelines
- Feature stores
- Model serving

### IoT & Sensors
- Time-series data
- Device management
- Edge computing
- Analytics

---

## Common Patterns

### RAG (Retrieval-Augmented Generation)
```sql
-- Store documents with embeddings
CREATE doc SET content, embedding;

-- Search
SELECT * FROM doc WHERE embedding <|5|> $query;

-- Hybrid
SELECT search::rrf([$text, $vector], 5, 60);
```

### Agent Memory
```sql
-- Session tracking
CREATE session SET user_id, status = 'active';

-- Entity extraction
CREATE entity SET session, type, name;

-- Decision tracing
CREATE decision SET session, action, result;
```

### Real-time Analytics
```sql
-- Live query
LIVE SELECT * FROM event;

-- Time-series
SELECT time::format(ts, '%Y-%m-%d'), count() 
FROM event GROUP BY time;
```

### Graph Relationships
```sql
-- Create edges
RELATE user -> follows -> user;
RELATE user -> bought -> product;

-- Traverse
SELECT <-follows<-user FROM user:alice;
```

---

## Resources

- [Case Studies](https://surrealdb.com/case-studies)
- [Benchmarks](https://surrealdb.com/benchmarks)