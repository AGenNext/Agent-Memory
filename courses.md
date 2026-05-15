# Agent Memory Courses
# All courses based on SurrealDB docs: https://surrealdb.com/docs

[courses]

# =====================================================
# COURSE 1: QUERYING FUNDAMENTALS
# =====================================================
[[courses.1]]
title = "Querying Fundamentals"
description = "Learn SurrealQL basics for CRUD operations"
level = "beginner"
duration = "2 hours"

[[courses.1.lessons]]
title = "Introduction to SurrealQL"
content = """
SurrealQL is SurrealDB's query language - combines SQL simplicity with NoSQL flexibility.
"""

[[courses.1.lessons.1]]
title = "CREATE - Inserting Data"
exercises = [
    "Create a simple record with CREATE",
    "Create record with specific ID",
    "Create multiple records",
    "Use time functions"
]
code = """
-- Basic create
CREATE session SET user_id = 'user:1', status = 'active';

-- With specific ID
CREATE session:session_001 SET user_id = 'user:1';

-- Set multiple fields
CREATE article:intro SET 
    title = 'Getting Started',
    content = 'Welcome to Agent Memory',
    created = time::now();

-- Create with nested objects
CREATE user:alice SET 
    profile = { name: 'Alice', bio: 'Developer' },
    settings = { theme: 'dark', notifications: true };
"""

[[courses.1.lessons.2]]
title = "SELECT - Reading Data"
exercises = [
    "Select all records",
    "Filter with WHERE",
    "Order and limit results",
    "Select specific fields"
]
code = """
-- Select all
SELECT * FROM session;

-- Filter
SELECT * FROM session WHERE user_id = 'user:alice';

-- With ordering
SELECT * FROM session ORDER BY started DESC LIMIT 10;

-- Nested field access
SELECT profile.name FROM user;

-- Graph traversal
SELECT ->has_entity->entity FROM session;
"""

[[courses.1.lessons.3]]
title = "UPDATE - Modifying Data"
exercises = [
    "Update single record",
    "Update with conditions",
    "Increment values",
    "Update nested fields"
]
code = """
-- Update record
UPDATE session:001 SET status = 'completed';

-- Conditional update
UPDATE session SET ended = time::now() 
WHERE status = 'active';

-- Increment
UPDATE product SET downloads = downloads + 1;

-- Nested update
UPDATE user:alice SET profile.bio = 'Updated bio';
"""

[[courses.1.lessons.4]]
title = "DELETE - Removing Data"
exercises = [
    "Delete single record",
    "Delete with conditions"
]
code = """
-- Delete specific
DELETE session:001;

-- Delete old sessions
DELETE FROM session WHERE started < time::now() - 30d;
"""


# =====================================================
# COURSE 2: ADVANCED QUERYING
# =====================================================
[[courses.2]]
title = "Advanced Querying"
description = "Live queries, full-text search, vectors"
level = "intermediate"
duration = "3 hours"

[[courses.2.lessons]]
title = "LIVE Queries - Real-time"
content = "Subscribe to data changes"
code = """
-- Live query
LIVE SELECT * FROM session WHERE status = 'active';

-- Live with specific fields
LIVE SELECT id, status, user_id FROM session;

-- Kill live query
KILL "query_id";
"""

title = "Full-Text Search"
content = "Search with relevance"
code = """
-- Create index
DEFINE INDEX search_idx ON article FIELDS content 
SEARCH ANALYZER exact BM25;

-- Search
SELECT * FROM article WHERE content @1@ 'agent memory';

-- With score
SELECT *, search::score(1) AS score 
FROM article WHERE content @1@ 'authentication' 
ORDER BY score DESC;
"""

title = "Vector Similarity"
content = "Embedding search"
code = """
-- Create HNSW index
DEFINE INDEX vec_idx ON article 
FIELDS embedding HNSW DIMENSION 512 DIST COSINE;

-- Similarity search
LET $query = [0.1, 0.2, 0.3, 0.4];
SELECT id, title, vector::distance::knn() AS dist
FROM article WHERE embedding <|5|> $query
ORDER BY dist ASC;
"""

title = "Hybrid Search"
content = "Combine text + vectors"
code = """
LET $text = SELECT id, search::score(1) AS s 
FROM article WHERE content @1@ 'query' ORDER BY s DESC LIMIT 5;

LET $vec = SELECT id, vector::distance::knn() AS d 
FROM article WHERE embedding <|5|> $emb;

SELECT search::rrf([$text, $vec], 5, 60);
"""


# =====================================================
# COURSE 3: DATA MODELS
# =====================================================
[[courses.3]]
title = "Data Models"
description = "Documents, graphs, vectors, time-series"
level = "beginner"
duration = "3 hours"

[[courses.3.lessons]]
title = "Document Model"
code = """
-- Nested documents
CREATE user SET 
    profile = {
        name: 'Alice',
        address: {
            city: 'NYC',
            country: 'USA'
        },
        tags: ['developer', 'ai']
    };

-- Query nested
SELECT profile.address.city FROM user;
SELECT user.profile.tags[0] FROM user;
"""

title = "Graph Model"
code = """
-- Create edge
RELATE user:alice -> wrote -> article:intro;

-- Bidirectional
RELATE article:intro <- authored <- user:alice;

-- With properties
RELATE user:alice -> rated -> article:intro SET rating = 5;

-- Traverse
SELECT <-authored<-article FROM user:alice;
SELECT ->wrote->article-><-references<-product FROM user:alice;
"""

title = "Vector Model"
code = """
-- Store embedding
CREATE article SET 
    title = 'RAG Guide',
    embedding = [0.1, 0.2, 0.3, 0.4];

-- Search
SELECT *, vector::distance::knn() FROM article 
WHERE embedding <|3|> $query;
"""

title = "Time-Series"
code = """
-- Time-ordered data
CREATE temperature SET 
    value = 22.5,
    recorded_at = time::now(),
    location = 'NYC';

-- Time range query
SELECT * FROM temperature 
WHERE recorded_at > d'2025-01-01' 
AND recorded_at < d'2025-01-31';

-- Aggregates
SELECT time::format(recorded_at, '%Y-%m') AS month,
       math::avg(value) AS avg_temp 
FROM temperature GROUP BY month;
"""


# =====================================================
# COURSE 4: GRAPH RELATIONSHIPS
# =====================================================
[[courses.4]]
title = "Graph Relationships"
description = "Entity relationships and traversal"
level = "intermediate"
duration = "2 hours"

[[courses.4.lessons]]
title = "Basic Relationships"
code = """
-- Simple edge
RELATE person:alice -> works_at -> company:acme;

-- With properties
RELATE person:alice -> employed_at -> company:acme SET 
    since = d'2023-01-01',
    role = 'Engineer';

-- Self-referential
RELATE person:alice -> knows -> person:bob;
"""

title = "Traversal"
code = """
-- 1 hop
SELECT ->works_at->company FROM person:alice;

-- 2 hops
SELECT ->works_at->company-><-product FROM person:alice;

-- Multi-hop with filtering
SELECT 
    ->works_at->company-><-references<-article 
WHERE content CONTAINS 'authentication'
FROM person:alice;
"""

title = "Path Operations"
code = """
-- Find paths
SELECT 
    ->knows->(? AS friend)->knows->(? AS friend_of_friend)
FROM person:alice;

-- Aggregation
SELECT 
    <-authored<-ticket->about->product-><-references<-article
    AS context
FROM user:alice;
"""


# =====================================================
# COURSE 5: SCHEMA MANAGEMENT
# =====================================================
[[courses.5]]
title = "Schema Management"
description = "Tables, fields, indexes, events"
level = "intermediate"
duration = "3 hours"

[[courses.5.lessons]]
title = "Tables"
code = """
-- Schemaless (default)
DEFINE TABLE session TYPE ANY SCHEMALESS;

-- Schemafull
DEFINE TABLE user TYPE ANY SCHEMAFULL;

-- Relation table
DEFINE TABLE like TYPE RELATION IN user OUT article;
"""

title = "Fields"
code = """
-- Required fields
DEFINE FIELD name ON user TYPE string ASSERT $value IS NOT NULL;

-- With default
DEFINE FIELD status ON session 
TYPE string DEFAULT 'active';

-- Enum constraint
DEFINE FIELD priority ON ticket 
TYPE string 
ASSERT $value IN ['low', 'medium', 'high'];
"""

title = "Indexes"
code = """
-- Unique index
DEFINE INDEX email ON user COLUMNS email UNIQUE;

-- Compound index
DEFINE INDEX session_user ON session 
COLUMNS user_id, started;

-- Full-text
DEFINE INDEX search ON article 
COLUMNS content SEARCH ANALYZER en BM25;

-- Vector (HNSW)
DEFINE INDEX vec ON article 
FIELDS embedding HNSW DIMENSION 512;
"""

title = "Events"
code = """
-- On create
DEFINE EVENT ON session WHEN $event = 'CREATE' THEN (
    CREATE log SET action = 'session_created', data = $this
);

-- On update
DEFINE EVENT ON ticket WHEN $before.status != 'resolved' 
AND $after.status = 'resolved' THEN (
    CREATE log SET action = 'ticket_resolved'
);
"""


# =====================================================
# COURSE 6: SECURITY
# =====================================================
[[courses.6]]
title = "Security & Auth"
description = "Authentication and permissions"
level = "intermediate"
duration = "2 hours"

[[courses.6.lessons]]
title = "Users"
code = """
-- Create user
DEFINE USER alice ON DATABASE PASSWORD 'secure123';

-- Role-based
DEFINE ROLE admin PERMISSIONS FULL;
DEFINE ROLE user PERMISSIONS 
    SELECT ON session, 
    CREATE ON entity,
    UPDATE ON entity WHERE user_id = $auth.id;
"""

title = "Scopes"
code = """
-- Define scope
DEFINE SCOPE api ENDPOINTS /*;

-- Grant access
GRANT api ON DATABASE TO alice;
"""

title = "Record Permissions"
code = """
-- Row-level security
DEFINE TABLE session PERMISSIONS 
    SELECT WHERE user_id = $auth.id,
    CREATE WHERE user_id = $auth.id,
    DELETE WHERE user_id = $auth.id;
"""

title = "JWT Auth"
code = """
-- Sign in
SIGNIN NAMESPACE memory DATABASE agent 
SCOPE api USER root PASSHASH $hash;

-- Verify token
SELECT * FROM session WHERE user_id = $auth.id;
"""


# =====================================================
# COURSE 7: AGENT MEMORY
# =====================================================
[[courses.7]]
title = "Agent Memory"
description = "Memory for AI agents"
level = "advanced"
duration = "4 hours"

[[courses.7.lessons]]
title = "Session Management"
code = """
-- Create conversation session
CREATE session SET 
    user_id = 'user:123',
    status = 'active',
    started = time::now();

-- Track decisions
CREATE decision SET 
    session = 'session:1',
    action = 'search',
    tool = 'article',
    result_summary = 'Found 3 articles';

-- Close session
UPDATE session SET 
    status = 'completed',
    ended = time::now();
"""

title = "Entity Extraction"
code = """
-- Extract entities
CREATE entity SET 
    session = 'session:1',
    type = 'person',
    name = 'Alice',
    properties = { email: 'alice@test.com' };

-- Link entities
RELATE entity:alice -> works_at -> entity:acme;
"""

title = "Knowledge Graph"
code = """
-- Create knowledge
CREATE knowledge SET 
    fact = 'Alice works at ACME',
    category = 'employment',
    source = 'user_input',
    valid_from = time::now();

-- Query graph
SELECT ->has_entity->entity 
FROM session WHERE user_id = 'user:1';
"""

title = "Hybrid Retrieval"
code = """
-- Combine sources
LET $semantic = SELECT * FROM article 
WHERE embedding <|3|> $query;

LET $graph = SELECT * FROM article 
WHERE ->references->product = $product;

LET $keywords = SELECT * FROM article 
WHERE content @1@ $query;

SELECT search::rrf([$semantic, $graph, $keywords], 5, 60);
"""


# =====================================================
# COURSE 8: REAL-TIME APPS
# =====================================================
[[courses.8]]
title = "Real-Time Applications"
description = "Live queries and subscriptions"
level = "intermediate"
duration = "2 hours"

[[courses.8.lessons]]
title = "Live Queries"
code = """
-- Subscribe to changes
LIVE SELECT * FROM session WHERE status = 'active';

-- Specific fields
LIVE SELECT id, status FROM message 
WHERE session = 'session:1';

-- Kill subscription
KILL "live_query_id";
"""

title = "Change Data Capture"
code = """
-- Enable CDC
DEFINE TABLE session CHANGE FEED 7d;

-- Query changes
SHOW CHANGES FOR TABLE session SINCE d'2025-01-01';
"""

title = "WebSocket Updates"
code = """
-- Subscribe via SDK
const db = new Surreal();
db.connect('ws://localhost:8000');

db.on('session:created', (session) => {
    console.log('New session:', session);
});
"""


# =====================================================
# COURSE 9: DEPLOYMENT
# =====================================================
[[courses.9]]
title = "Deployment"
description = "Self-hosted, Docker, Cloud"
level = "beginner"
duration = "2 hours"

[[courses.9.lessons]]
title = "Docker"
code = """
# docker-compose.yml
services:
  surrealdb:
    image: surrealdb/surrealdb:latest
    ports:
      - "8000:8000"
    command: start --user root --pass root memory

# Run
docker-compose up -d
"""

title = "Self-Hosted"
code = """
# Install
curl -sSf https://install.surrealdb.com | sh

# Start with RocksDB
surreal start --user root --pass root rocksdb:///data/db

# Start with SurrealKV
surreal start --user root --pass root surrealkv:///data/db

# Distributed
surreal start --user root --pass root tikv://localhost:2379
"""

title = "Embedded (WASM)"
code = """
# Browser/Node.js
import { Surreal } from '@surrealdb/wasm'

const db = new Surreal()
await db.connect('indexeddb://agent-memory')
await db.use({ namespace: 'memory', database: 'agent' })
"""


# =====================================================
# COURSE 10: TOOLS & EXTENSIONS
# =====================================================
[[courses.10]]
title = "Tools & Extensions"
description = "SurrealKit, SurrealML, WASM"
level = "advanced"
duration = "3 hours"

[[courses.10.lessons]]
title = "SurrealKit - Migrations"
code = """
# surrealkit.toml
[project]
name = "agent-memory"

[sync]
paths = ["surql/*.surql"]

# Commands
surrealkit sync      # Sync schema
surrealkit seed     # Seed data
surrealkit test     # Run tests
"""

title = "SurrealML - In-DB ML"
code = """
# Train in Python
from surrealdbMl import SurrealMl

model = SurrealMl(classifier, ['text'], 'sentiment')
model.save('sentiment.surml')

# Infer in SurrealQL
SELECT ml::predict('sentiment', { text: 'I love it!' }) 
FROM feedback;
"""

title = "WASM Extensions"
code = """
# Write in Rust
#[surrealism]
fn process_input(input: String) -> String {
    format!("Processed: {}", input)
}

# Compile
surreal module build

# Use in SurrealQL
SELECT mod::my_extension::process_input('data');
"""


# =====================================================
# COURSE 11: INTEGRATIONS
# =====================================================
[[courses.11]]
title = "Integrations"
description = "AI frameworks, tools"
level = "intermediate"
duration = "2 hours"

[[courses.11.lessons]]
title = "OpenAI Integration"
code = """
# Generate embeddings
from openai import AsyncOpenAI

client = AsyncOpenAI()
embedding = await client.embeddings.create(
    model='text-embedding-3-small',
    input='Agent memory explanation'
)

# Store in SurrealDB
CREATE article SET 
    content = '...',
    embedding = embedding.data[0].embedding;
"""

title = "LangChain"
code = """
from langchain_openai import OpenAIEmbeddings
from surrealdb import SurrealDB

embeddings = OpenAIEmbeddings()
db = SurrealDB('ws://localhost:8000')
"""

title = "MCP Server"
code = """
# SurrealDB as MCP tool
# Connect via Model Context Protocol
# Tools: query, create, update, search
"""


# =====================================================
# COURSE 12: PERFORMANCE
# =====================================================
[[courses.12]]
title = "Performance & Optimization"
description = "Indexes, queries, scaling"
level = "advanced"
duration = "2 hours"

[[courses.12.lessons]]
title = "Indexing Strategies"
code = """
-- Choose right index type
DEFINE INDEX user_email ON user COLUMNS email UNIQUE;
DEFINE INDEX session_user_time ON session 
COLUMNS user_id, started DESC;

-- Partial indexes
DEFINE INDEX active ON session 
COLUMNS started 
WHERE status = 'active';
"""

title = "Query Optimization"
code = """
-- Use specific fields
SELECT id, status FROM session;

-- Limit results
SELECT * FROM article LIMIT 100;

-- Avoid SELECT *
-- Bad: SELECT * FROM large_table
-- Good: SELECT id, name FROM large_table
"""

title = "Scaling"
code = """
-- Read replicas
surrealdb:
    command: start --enable-spaces ...

-- SurrealKV for large datasets
surreal start surrealkv:///data/db

-- TiKV for distributed
surreal start tikv://pd:2379
"""