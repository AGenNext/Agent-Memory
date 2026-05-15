-- =====================================================
-- Agent Memory Sample Queries
-- Based on SurrealDB docs: https://surrealdb.com/docs/sample-queries
-- =====================================================

-- =====================================================
-- 1. CREATE - Creating Records
-- =====================================================

-- Create a session with auto-generated ID
CREATE session SET 
    user_id = 'user:alice',
    status = 'active',
    started = time::now();

-- Create session with specific ID
CREATE session:session_001 SET 
    user_id = 'user:alice',
    status = 'active',
    started = time::now();

-- Create an article with embedding
CREATE article:intro SET
    title = 'Getting Started with Agent Memory',
    category = 'documentation',
    content = 'Agent Memory enables persistent context for AI agents...',
    embedding = [0.1, 0.2, 0.3, 0.4],
    created = time::now();

-- Create product
CREATE product:auth_service SET
    name = 'Authentication Service',
    version = '1.0.0',
    description = 'Handle user authentication and authorization',
    created = time::now();

-- =====================================================
-- 2. SELECT - Reading Data
-- =====================================================

-- Select all sessions
SELECT * FROM session;

-- Select all sessions for a user
SELECT * FROM session WHERE user_id = 'user:alice';

-- Select with ordering and limit
SELECT * FROM session 
WHERE user_id = 'user:alice' 
ORDER BY started DESC 
LIMIT 10;

-- Select specific fields
SELECT id, status, started, ended FROM session;

-- Select with pagination
SELECT * FROM session 
WHERE status = 'active' 
LIMIT 5 
START 10;

-- Nested field selection
SELECT 
    user_id,
    started,
    ended,
    (SELECT count() FROM entity WHERE session = session.id) AS entity_count
FROM session
WHERE user_id = 'user:alice';

-- =====================================================
-- 3. UPDATE - Modifying Records
-- =====================================================

-- Update session status
UPDATE session:session_001 SET 
    status = 'completed',
    ended = time::now();

-- Update multiple fields
UPDATE article:intro SET
    title = 'Getting Started with Agent Memory (Updated)',
    updated = time::now();

-- Increment a counter (if exists)
UPDATE product:auth_service SET 
    downloads = downloads + 1;

-- =====================================================
-- 4. DELETE - Removing Records
-- =====================================================

-- Delete a specific record
DELETE session:session_001;

-- Delete with condition
DELETE FROM session 
WHERE status = 'cancelled' 
AND started < time::now() - 7d;

-- =====================================================
-- 5. RELATE - Graph Relationships
-- =====================================================

-- Link article to product (references)
RELATE article:intro->references->product:auth_service;

-- Link ticket to product (about)
RELATE ticket:ticket_001->about->product:auth_service;

-- Link ticket to solution (resolved_by)
RELATE ticket:ticket_001->resolved_by->solution:solution_001;

-- Link ticket to user (authored)
RELATE ticket:ticket_001->authored->user:alice;

-- Set properties on relationship
RELATE session:session_001->led_to->decision:decision_001 SET
    order = 1,
    time_taken = 150ms;

-- =====================================================
-- 6. GRAPH - Traversal
-- =====================================================

-- Get entity with related entities
SELECT *, 
    ->has_entity->entity AS related_entities
FROM session:session_001;

-- Get article with products it references
SELECT 
    id,
    title,
    ->references->product AS products
FROM article:intro;

-- Get product with related tickets
SELECT 
    id,
    name,
    <-about<-ticket AS tickets
FROM product:auth_service;

-- Multi-hop traversal
SELECT 
    <-authored<-ticket->about->product-><-references<-article AS context
FROM user:alice;

-- =====================================================
-- 7. LIVE - Real-time Queries
-- =====================================================

-- Live query for new sessions
LIVE SELECT * FROM session WHERE status = 'active';

-- Live query for decisions
LIVE SELECT * FROM decision_step WHERE session = 'session:session_001';

-- Live query for new entities
LIVE SELECT * FROM entity;

-- Kill a live query
KILL "query_id_here";

-- =====================================================
-- 8. FULLTEXT - Search
-- =====================================================

-- Search articles by text
SELECT * FROM article 
WHERE content @1@ 'authentication';

-- Search with ordering by relevance
SELECT *, search::score(1) AS score 
FROM article 
WHERE content @1@ 'authentication' 
ORDER BY score DESC;

-- Search multiple terms
SELECT * FROM article 
WHERE content @1@ 'agent memory';

-- =====================================================
-- 9. VECTOR - Similarity Search
-- =====================================================

-- Find similar articles by embedding
LET $query = [0.1, 0.2, 0.3, 0.4];
SELECT id, title, vector::distance::knn() AS distance
FROM article
WHERE embedding <|5|> $query
ORDER BY distance ASC;

-- Hybrid: text + vector (reciprocal rank fusion)
LET $text_results = (
    SELECT id, search::score(1) AS score 
    FROM article 
    WHERE content @1@ 'agent memory'
    ORDER BY score DESC LIMIT 5
);
LET $vec_results = (
    SELECT id, vector::distance::knn() AS distance 
    FROM article 
    WHERE embedding <|5|> [0.1, 0.2, 0.3]
);
SELECT search::rrf([$text_results, $vec_results], 5, 60) AS results;

-- =====================================================
-- 10. FUNCTIONS - Custom Functions
-- =====================================================

-- Call hybrid search function
SELECT fn::hybrid_search('how to reset password', 5, 60);

-- Get session summary
SELECT fn::session_summary('session:session_001');

-- Check rate limit
SELECT fn::check_rate_limit('user:alice', '/api/sessions', 100, 60s);

-- Calculate token cost
SELECT fn::token_cost(1000, 500, 'gpt-4o');

-- =====================================================
-- 11. AGGREGATES - Grouping & Analytics
-- =====================================================

-- Count by status
SELECT status, count() AS count FROM session GROUP BY status;

-- Count by user
SELECT user_id, count() AS sessions FROM session GROUP BY user_id;

-- Average score
SELECT math::avg(weight) AS avg_weight FROM solution;

-- Sum downloads
SELECT math::sum(downloads) AS total_downloads FROM product GROUP ALL;

-- Time-based grouping
SELECT 
    time::format(started, '%Y-%m') AS month,
    count() AS sessions
FROM session 
GROUP BY month;

-- =====================================================
-- 12. TEMPORAL - Version Queries
-- =====================================================

-- Get historical version (SurrealKV with versioning)
SELECT * FROM entity VERSION d'2025-01-01T00:00:00Z';

-- Get all versions of a record
SELECT * FROM entity VALID ALL;

-- Query valid at specific time
SELECT * FROM fact WHERE valid_from <= d'2025-06-15' AND valid_to >= d'2025-06-15';

-- =====================================================
-- 13. EVENTS - Table Events
-- =====================================================

-- Events fire automatically on table changes
-- (defined in schema, not queried directly)

-- =====================================================
-- 14. TRANSACTIONS - Atomic Operations
-- =====================================================

-- Transaction with multiple operations
BEGIN;
CREATE session:tx SET user_id = 'user:bob', status = 'active';
CREATE entity:e1 SET session = 'session:tx', type = 'person', name = 'Bob';
RELATE session:tx->has_entity->entity:e1;
COMMIT;

-- Rollback on error
BEGIN;
CREATE session:cancel_test SET user_id = 'user:temp', status = 'test';
ROLLBACK;

-- =====================================================
-- 15. PARAMETERS - Query Variables
-- =====================================================

-- Define and use parameters
LET $user = 'user:alice';
LET $limit = 10;

SELECT * FROM session WHERE user_id = $user LIMIT $limit;

-- Using parameters block
{
    "user": "user:alice",
    "limit": 10
}
SELECT * FROM session WHERE user_id = $user LIMIT $limit;

-- =====================================================
-- 16. IF/ELSE - Conditional Logic
-- =====================================================

-- Conditional in query
SELECT id, 
    IF status = 'completed' THEN 'done' ELSE 'pending' END 
    AS state
FROM session;

-- Match statement
SELECT 
    IF status {
        'active' => 'In Progress',
        'completed' => 'Done',
        'cancelled' => 'Cancelled'
    } 
    AS status_text
FROM session;

-- =====================================================
-- 17. ARRAY - Array Operations
-- =====================================================

-- Array contains
SELECT * FROM article WHERE tags CONTAINS 'documentation';

-- Array contains any
SELECT * FROM user WHERE roles CONTAINSANY ['admin', 'moderator'];

-- Array length
SELECT array::len(emails) AS email_count FROM user;

-- =====================================================
-- 18. STRING - String Operations
-- =====================================================

-- String contains
SELECT * FROM article WHERE title CONTAINS 'Getting Started';

-- String starts with
SELECT * FROM product WHERE name STARTSWITH 'Auth';

-- String ends with
SELECT * FROM user WHERE email ENDSWITH '@example.com';

-- String join
SELECT string::join(' ', first_name, last_name) AS full_name FROM user;

-- =====================================================
-- 19. MATH - Mathematical Operations
-- =====================================================

-- Math functions
SELECT 
    math::round(price) AS price,
    math::floor(price) AS floor,
    math::ceil(price) AS ceil,
    math::abs(-5) AS abs,
    math::sqrt(16) AS sqrt
FROM product;

-- Mathematical constants
SELECT math::PI AS pi, math::E AS e, math::TAU AS tau;

-- =====================================================
-- 20. TYPE - Type Conversion
-- =====================================================

-- Type casting
SELECT * FROM session 
WHERE string::len(id) > 10;

-- Type conversion
SELECT int::cast('42') AS number;
SELECT string::cast(42) AS text;
SELECT float::cast('3.14') AS decimal;