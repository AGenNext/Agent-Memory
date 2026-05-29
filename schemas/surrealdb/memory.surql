-- =============================================================================
-- Agent-Memory · SurrealDB Schema
-- =============================================================================
-- Design sources:
--   MUST  → Spectron (SurrealDB): 6 typed categories, tri-temporal, provenance,
--            supersede-not-overwrite, calibration, retrieval traces
--   VALUE → A-Mem: memory evolution events (context updates on related memories)
--   VALUE → Spacebot Cortex: working_memory table for background synthesis
-- =============================================================================

-- ---------------------------------------------------------------------------
-- NAMESPACE / DATABASE assumed set by caller:
--   USE NS agnxxt DB agent_memory;
-- ---------------------------------------------------------------------------


-- =============================================================================
-- 1. MEMORY
-- =============================================================================
-- Six typed categories (Spectron):
--   episodic    raw conversational record — source of truth for all extractions
--   identity    durable facts about an agent or user (name, role, preferences)
--   knowledge   things the agent/user has learnt; decays without reinforcement
--   context     active working context for the current conversation; short-lived
--   instruction behavioural directives — applied at prompt assembly, not retrieval
--   uncertainty explicit "we don't know yet" rows emitted by the reconciler

DEFINE TABLE memory SCHEMAFULL;

-- Category & content
DEFINE FIELD category          ON TABLE memory TYPE string
    ASSERT $value IN [
        'episodic', 'identity', 'knowledge',
        'context', 'instruction', 'uncertainty'
    ];
DEFINE FIELD content           ON TABLE memory TYPE string;
DEFINE FIELD summary           ON TABLE memory TYPE option<string>;

-- Scope & ownership
DEFINE FIELD agent_id          ON TABLE memory TYPE string;
DEFINE FIELD session_id        ON TABLE memory TYPE option<string>;
DEFINE FIELD scope             ON TABLE memory TYPE string DEFAULT 'agent'
    ASSERT $value IN ['agent', 'team', 'org', 'project'];

-- Tri-temporal (Spectron)
-- system_time   → SurrealDB MVCC handles this; use VERSION queries
-- known_time    → when Spectron (or we) first believed this fact
-- valid_time_*  → when the assertion held / holds in the world
DEFINE FIELD known_time        ON TABLE memory TYPE datetime VALUE time::now();
DEFINE FIELD valid_time_start  ON TABLE memory TYPE option<datetime>;
DEFINE FIELD valid_time_end    ON TABLE memory TYPE option<datetime>;

-- Provenance (Spectron)
DEFINE FIELD source_kind       ON TABLE memory TYPE string DEFAULT 'agent_turn'
    ASSERT $value IN [
        'agent_turn', 'user_turn', 'document', 'reflection',
        'elaboration', 'consolidation', 'tool_output', 'external'
    ];
DEFINE FIELD source_ref        ON TABLE memory TYPE option<string>;   -- turn_id / doc_id
DEFINE FIELD source_trust      ON TABLE memory TYPE float DEFAULT 0.7; -- 0.0–1.0
DEFINE FIELD derived_from      ON TABLE memory TYPE option<array<record<memory>>>;

-- Calibration (Spectron)
DEFINE FIELD confidence        ON TABLE memory TYPE float DEFAULT 0.8; -- reconciler posterior
DEFINE FIELD importance        ON TABLE memory TYPE float DEFAULT 0.5;

-- Supersession (Spectron: supersede-not-overwrite)
DEFINE FIELD superseded        ON TABLE memory TYPE bool DEFAULT false;
DEFINE FIELD superseded_at     ON TABLE memory TYPE option<datetime>;
DEFINE FIELD superseded_by     ON TABLE memory TYPE option<record<memory>>;

-- A-Mem evolution fields
DEFINE FIELD keywords          ON TABLE memory TYPE option<array<string>>;
DEFINE FIELD tags              ON TABLE memory TYPE option<array<string>>;
DEFINE FIELD evolved_at        ON TABLE memory TYPE option<datetime>;

-- Vector embedding
DEFINE FIELD embedding         ON TABLE memory FLEXIBLE TYPE option<array<float>>;

DEFINE FIELD created_at        ON TABLE memory TYPE datetime VALUE time::now();
DEFINE FIELD updated_at        ON TABLE memory TYPE datetime VALUE time::now();

-- Indexes
DEFINE INDEX memory_agent_idx       ON TABLE memory FIELDS agent_id;
DEFINE INDEX memory_category_idx    ON TABLE memory FIELDS category;
DEFINE INDEX memory_scope_idx       ON TABLE memory FIELDS scope;
DEFINE INDEX memory_active_idx      ON TABLE memory FIELDS agent_id, superseded;
DEFINE INDEX memory_embedding_idx   ON TABLE memory FIELDS embedding
    HNSW DIMENSION 1536 DIST COSINE;
DEFINE INDEX memory_content_fts     ON TABLE memory FIELDS content
    SEARCH ANALYZER ascii BM25;


-- =============================================================================
-- 2. MEMORY EDGES  (graph relations — Spectron + Spacebot)
-- =============================================================================
-- Edge types:
--   related_to      semantic similarity / shared context
--   updates         this memory refines or supersedes another
--   contradicts     explicit conflict (emits uncertainty row)
--   caused_by       causal / temporal dependency
--   part_of         containment / hierarchical grouping

DEFINE TABLE mem_edge TYPE RELATION IN memory OUT memory SCHEMAFULL;

DEFINE FIELD kind ON TABLE mem_edge TYPE string
    ASSERT $value IN [
        'related_to', 'updates', 'contradicts', 'caused_by', 'part_of'
    ];
DEFINE FIELD weight        ON TABLE mem_edge TYPE float DEFAULT 1.0;
DEFINE FIELD created_at    ON TABLE mem_edge TYPE datetime VALUE time::now();

DEFINE INDEX mem_edge_kind_idx ON TABLE mem_edge FIELDS kind;


-- =============================================================================
-- 3. RETRIEVAL TRACE  (Spectron: traces are first-class memory)
-- =============================================================================
-- Every read emits a trace. The ranker reads its own history:
--   rows useful for similar queries → boosted
--   rows associated with corrections → demoted

DEFINE TABLE retrieval_trace SCHEMAFULL;

DEFINE FIELD agent_id      ON TABLE retrieval_trace TYPE string;
DEFINE FIELD session_id    ON TABLE retrieval_trace TYPE option<string>;
DEFINE FIELD query_text    ON TABLE retrieval_trace TYPE string;
DEFINE FIELD query_embedding ON TABLE retrieval_trace FLEXIBLE TYPE option<array<float>>;

-- Tier reached (Spectron four-tier ladder)
--   1 = direct_lookup, 2 = response_reuse, 3 = hybrid, 4 = full_context
DEFINE FIELD tier          ON TABLE retrieval_trace TYPE int DEFAULT 3;

-- Results returned
DEFINE FIELD result_ids    ON TABLE retrieval_trace TYPE array<record<memory>>;
DEFINE FIELD result_scores ON TABLE retrieval_trace FLEXIBLE TYPE option<array<float>>;

-- Feedback (for trace-derived ranking boost/demote)
DEFINE FIELD useful        ON TABLE retrieval_trace TYPE option<bool>;
DEFINE FIELD correction    ON TABLE retrieval_trace TYPE option<bool>;

DEFINE FIELD created_at    ON TABLE retrieval_trace TYPE datetime VALUE time::now();

DEFINE INDEX trace_agent_idx   ON TABLE retrieval_trace FIELDS agent_id;
DEFINE INDEX trace_session_idx ON TABLE retrieval_trace FIELDS session_id;


-- =============================================================================
-- 4. DECISION TRACE  (audit + policy)
-- =============================================================================

DEFINE TABLE decision_trace SCHEMAFULL;

DEFINE FIELD run_id        ON TABLE decision_trace TYPE string;
DEFINE FIELD step_id       ON TABLE decision_trace TYPE string;
DEFINE FIELD agent_id      ON TABLE decision_trace TYPE string;
DEFINE FIELD actor         ON TABLE decision_trace TYPE option<string>;
DEFINE FIELD action        ON TABLE decision_trace TYPE string;
DEFINE FIELD input         ON TABLE decision_trace FLEXIBLE TYPE object;
DEFINE FIELD output        ON TABLE decision_trace FLEXIBLE TYPE object;
DEFINE FIELD status        ON TABLE decision_trace TYPE string
    ASSERT $value IN ['pending', 'success', 'failed', 'rejected'];
DEFINE FIELD memory_refs   ON TABLE decision_trace TYPE option<array<record<memory>>>;
DEFINE FIELD created_at    ON TABLE decision_trace TYPE datetime VALUE time::now();

DEFINE INDEX dt_run_idx    ON TABLE decision_trace FIELDS run_id;
DEFINE INDEX dt_agent_idx  ON TABLE decision_trace FIELDS agent_id;


-- =============================================================================
-- 5. WORKING MEMORY  (Spacebot Cortex pattern)
-- =============================================================================
-- Background-synthesised, not written per LLM call.
-- Layers:
--   identity_context     stable agent identity briefing
--   intraday_synthesis   compressed narrative of today's events (rebuilt hourly)
--   daily_rollup         midnight summary replacing the day's intraday layer
--   cross_agent_map      activity snapshot across all agents in scope
--   knowledge_brief      change-driven synthesis; regenerated when graph changes

DEFINE TABLE working_memory SCHEMAFULL;

DEFINE FIELD agent_id      ON TABLE working_memory TYPE string;
DEFINE FIELD layer         ON TABLE working_memory TYPE string
    ASSERT $value IN [
        'identity_context', 'intraday_synthesis', 'daily_rollup',
        'cross_agent_map', 'knowledge_brief'
    ];
DEFINE FIELD content       ON TABLE working_memory TYPE string;
DEFINE FIELD source_memories ON TABLE working_memory TYPE option<array<record<memory>>>;
DEFINE FIELD valid_date    ON TABLE working_memory TYPE option<datetime>; -- for daily rollup
DEFINE FIELD token_count   ON TABLE working_memory TYPE option<int>;
DEFINE FIELD created_at    ON TABLE working_memory TYPE datetime VALUE time::now();
DEFINE FIELD updated_at    ON TABLE working_memory TYPE datetime VALUE time::now();

DEFINE INDEX wm_agent_layer_idx ON TABLE working_memory FIELDS agent_id, layer UNIQUE;


-- =============================================================================
-- 6. EVENTS (A-Mem evolution trigger)
-- =============================================================================
-- When a new memory is created, fire an evolution event so related memories
-- can be updated by the reconciler service (Python-side, not LLM-in-DB).

DEFINE EVENT memory_created ON TABLE memory
    WHEN $event = "CREATE"
    THEN {
        CREATE evolution_queue SET
            new_memory_id   = $value.id,
            agent_id        = $value.agent_id,
            category        = $value.category,
            status          = 'pending',
            created_at      = time::now()
    };


-- =============================================================================
-- 7. EVOLUTION QUEUE  (A-Mem: memory evolution jobs)
-- =============================================================================

DEFINE TABLE evolution_queue SCHEMAFULL;

DEFINE FIELD new_memory_id ON TABLE evolution_queue TYPE record<memory>;
DEFINE FIELD agent_id      ON TABLE evolution_queue TYPE string;
DEFINE FIELD category      ON TABLE evolution_queue TYPE string;
DEFINE FIELD status        ON TABLE evolution_queue TYPE string DEFAULT 'pending'
    ASSERT $value IN ['pending', 'processing', 'done', 'skipped'];
DEFINE FIELD processed_at  ON TABLE evolution_queue TYPE option<datetime>;
DEFINE FIELD created_at    ON TABLE evolution_queue TYPE datetime VALUE time::now();

DEFINE INDEX eq_status_idx ON TABLE evolution_queue FIELDS status;
DEFINE INDEX eq_agent_idx  ON TABLE evolution_queue FIELDS agent_id;
