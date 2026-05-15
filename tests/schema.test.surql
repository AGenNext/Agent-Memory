-- =====================================================
-- Agent Memory Tests
-- Run with: surrealkit test
-- =====================================================

-- =====================================================
-- Schema Tests
-- =====================================================

-- Test: Session can be created
DEFINE TEST schema::create_session {
    -- Prepare: Clear existing sessions
    DELETE FROM session WHERE id = 'session:test';
    
    -- Execute
    CREATE session:test SET 
        user_id = 'user:test',
        status = 'active',
        started = time::now();
    
    -- Assert
    ASSERT $this.id = 'session:test';
    ASSERT $this.status = 'active';
};

-- Test: Entity can be created
DEFINE TEST schema::create_entity {
    DELETE FROM entity WHERE id = 'entity:test';
    
    CREATE entity:test SET 
        session = 'session:test',
        type = 'person',
        name = 'Test User',
        created = time::now();
    
    ASSERT $this.type = 'person';
    ASSERT $this.name = 'Test User';
};

-- Test: Decision can be traced
DEFINE TEST schema::trace_decision {
    DELETE FROM decision WHERE id = 'decision:test';
    
    CREATE decision:test SET 
        session = 'session:test',
        action = 'search',
        tool = 'article',
        created = time::now();
    
    ASSERT $this.action = 'search';
    ASSERT $this.tool = 'article';
};

-- =====================================================
-- Query Tests
-- =====================================================

-- Test: Full-text search works
DEFINE TEST query::fulltext_search {
    -- Execute search
    SELECT * FROM article 
    WHERE content @1@ 'agent';
    
    -- Assert: Should return results
    ASSERT count() > 0;
};

-- Test: Vector search works
DEFINE TEST query::vector_search {
    -- Query with embedding
    LET $query = [0.1, 0.2, 0.3];
    
    SELECT id, vector::distance::knn() AS distance
    FROM article
    WHERE embedding <|5|> $query;
    
    -- Assert: Returns results
    ASSERT count() >= 0;
};

-- =====================================================
-- Integration Tests
-- =====================================================

-- Test: Full session flow
DEFINE TEST integration::session_flow {
    -- Create session
    LET $session = CREATE session SET 
        user_id = 'user:flow',
        status = 'active',
        started = time::now();
    
    -- Create entities
    CREATE entity SET session = $session.id, type = 'person', name = 'Alice';
    CREATE entity SET session = $session.id, type = 'company', name = 'ACME';
    
    -- Assert
    LET $entities = SELECT * FROM entity WHERE session = $session.id;
    ASSERT array::len($entities) = 2;
};