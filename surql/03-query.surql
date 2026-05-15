-- =====================================================
-- QUERY: Retrieval Patterns
-- =====================================================

-- === Vector Search ===
-- Semantic search over articles using embeddings
SELECT id, title, category, content, vector::distance::knn() AS distance
FROM article
WHERE embedding <|5,100|> $query_embedding;

-- === Graph Traversal ===
-- Find related products from article
SELECT 
    title, category, content,
    ->references->product.{name, version} AS products,
    ->related_to->article.{title, category} AS related_articles
FROM type::record("article:auth");

-- Traverse: product -> tickets -> solutions
SELECT 
    name,
    <-about<-ticket.{subject, status, priority} AS tickets,
    <-about<-ticket->resolved_by[
        WHERE weight > 0.5 
        AND (valid_until IS NONE OR valid_until > time::now())
    ]->solution.{title, steps, verified} AS solutions,
    ->depends_on->product.name AS dependencies
FROM type::record("product:auth");

-- === Hybrid Retrieval ===
-- Combine vector search with graph traversal
LET $emb = $query_embedding;
SELECT id, title, vector::distance::knn() AS distance
FROM article
WHERE embedding <|3,50|> $emb
FETCH id, title, category;

-- Query: Find solutions for tickets about a product
SELECT 
    ticket.subject,
    ticket.status,
    solution.title AS resolution,
    solution.steps,
    solution.verified
FROM ticket
WHERE ->about->product = type::record("product:auth")
AND ticket.status = "resolved"
FETCH ticket.subject, solution.title, solution.steps, solution.verified;

-- === Decision Tracing ===
-- Review past decisions for similar queries
SELECT 
    query, response, model, created,
    vector::distance::knn() AS similarity
FROM response_trace
WHERE query_embedding <|3,100|> $query_embedding
AND session != $current_session
ORDER BY similarity ASC;

-- Trace retrieval steps for auditing
SELECT 
    session,
    method,
    query_text,
    entity_ids,
    distances,
    created
FROM retrieval_trace
WHERE session = $session_id
ORDER BY created ASC;

-- === Temporal Queries ===
-- What was true at a specific point in time
SELECT *
FROM solution
WHERE created < $point_in_time
AND (valid_until IS NONE OR valid_until > $point_in_time);

-- Recent decisions in a session
SELECT 
    step, action, tool, result_summary, created
FROM decision_step
WHERE session = $session_id
ORDER BY step ASC;