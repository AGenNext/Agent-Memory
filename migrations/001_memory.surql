-- =============================================================================
-- Agent-Memory v0.1 — SurrealDB embedded schema
-- Applied at binary boot via Store::migrate()
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. MEMORY
-- Six typed categories (Spectron model):
--   episodic     raw conversational record — source of truth
--   identity     durable facts about agent or user
--   knowledge    learnt things; decays without reinforcement
--   context      active working context for current conversation
--   instruction  behavioural directives; applied at prompt assembly
--   uncertainty  explicit "we don't know yet" — emitted by reconciler
-- ---------------------------------------------------------------------------

-- Full-text analyzer used by the BM25 content index below.
DEFINE ANALYZER IF NOT EXISTS ascii
    TOKENIZERS blank, class
    FILTERS lowercase, ascii;

DEFINE TABLE memory SCHEMAFULL;

DEFINE FIELD category         ON TABLE memory TYPE string
    ASSERT $value IN ['episodic','identity','knowledge','context','instruction','uncertainty'];
DEFINE FIELD content          ON TABLE memory TYPE string;
DEFINE FIELD summary          ON TABLE memory TYPE option<string>;

-- Ownership
DEFINE FIELD agent_id         ON TABLE memory TYPE string;
DEFINE FIELD session_id       ON TABLE memory TYPE option<string>;
DEFINE FIELD scope            ON TABLE memory TYPE string DEFAULT 'agent'
    ASSERT $value IN ['agent','team','org','project'];

-- Tri-temporal
-- system_time  → SurrealDB MVCC (VERSION queries)
-- known_time   → when we first believed this fact
-- valid_time_* → when the assertion held in the world
DEFINE FIELD known_time       ON TABLE memory TYPE datetime VALUE time::now();
DEFINE FIELD valid_time_start ON TABLE memory TYPE option<datetime>;
DEFINE FIELD valid_time_end   ON TABLE memory TYPE option<datetime>;

-- Provenance
DEFINE FIELD source_kind      ON TABLE memory TYPE string DEFAULT 'agent_turn'
    ASSERT $value IN ['agent_turn','user_turn','document','reflection','elaboration','consolidation','tool_output','external'];
DEFINE FIELD source_ref       ON TABLE memory TYPE option<string>;
DEFINE FIELD source_trust     ON TABLE memory TYPE float DEFAULT 0.7;
DEFINE FIELD derived_from     ON TABLE memory TYPE option<array<record<memory>>>;

-- Calibration
DEFINE FIELD confidence       ON TABLE memory TYPE float DEFAULT 0.8;
DEFINE FIELD importance       ON TABLE memory TYPE float DEFAULT 0.5;

-- Supersession (never overwrite — always supersede)
DEFINE FIELD superseded       ON TABLE memory TYPE bool DEFAULT false;
DEFINE FIELD superseded_at    ON TABLE memory TYPE option<datetime>;
DEFINE FIELD superseded_by    ON TABLE memory TYPE option<record<memory>>;

-- Evolution (A-Mem)
DEFINE FIELD keywords         ON TABLE memory TYPE option<array<string>>;
DEFINE FIELD tags             ON TABLE memory TYPE option<array<string>>;
DEFINE FIELD evolved_at       ON TABLE memory TYPE option<datetime>;

-- Vector embedding (1536-dim OpenAI / compatible)
DEFINE FIELD embedding        ON TABLE memory TYPE option<array<float>>;

DEFINE FIELD created_at       ON TABLE memory TYPE datetime VALUE time::now();
DEFINE FIELD updated_at       ON TABLE memory TYPE datetime VALUE time::now();

-- Indexes
DEFINE INDEX memory_agent_idx    ON TABLE memory FIELDS agent_id;
DEFINE INDEX memory_category_idx ON TABLE memory FIELDS category;
DEFINE INDEX memory_active_idx   ON TABLE memory FIELDS agent_id, superseded;
DEFINE INDEX memory_embedding_idx ON TABLE memory FIELDS embedding
    HNSW DIMENSION 1536 DIST COSINE;
DEFINE INDEX memory_content_fts  ON TABLE memory FIELDS content
    FULLTEXT ANALYZER ascii BM25;

-- ---------------------------------------------------------------------------
-- 2. MEMORY EDGES — graph relations
-- ---------------------------------------------------------------------------

DEFINE TABLE mem_edge TYPE RELATION IN memory OUT memory SCHEMAFULL;

DEFINE FIELD kind       ON TABLE mem_edge TYPE string
    ASSERT $value IN ['related_to','updates','contradicts','caused_by','part_of'];
DEFINE FIELD weight     ON TABLE mem_edge TYPE float DEFAULT 1.0;
DEFINE FIELD created_at ON TABLE mem_edge TYPE datetime VALUE time::now();

DEFINE INDEX mem_edge_kind_idx ON TABLE mem_edge FIELDS kind;

-- ---------------------------------------------------------------------------
-- 3. RETRIEVAL TRACE — every read is recorded
-- Ranker reads its own history: useful rows boosted, corrections demoted
-- ---------------------------------------------------------------------------

DEFINE TABLE retrieval_trace SCHEMAFULL;

DEFINE FIELD agent_id        ON TABLE retrieval_trace TYPE string;
DEFINE FIELD session_id      ON TABLE retrieval_trace TYPE option<string>;
DEFINE FIELD query_text      ON TABLE retrieval_trace TYPE string;
DEFINE FIELD query_embedding ON TABLE retrieval_trace TYPE option<array<float>>;
-- tier: 1=direct_lookup 2=response_reuse 3=hybrid 4=full_context
DEFINE FIELD tier            ON TABLE retrieval_trace TYPE int DEFAULT 3;
DEFINE FIELD result_ids      ON TABLE retrieval_trace TYPE array<record<memory>>;
DEFINE FIELD result_scores   ON TABLE retrieval_trace TYPE option<array<float>>;
DEFINE FIELD useful          ON TABLE retrieval_trace TYPE option<bool>;
DEFINE FIELD correction      ON TABLE retrieval_trace TYPE option<bool>;
DEFINE FIELD created_at      ON TABLE retrieval_trace TYPE datetime VALUE time::now();

DEFINE INDEX trace_agent_idx   ON TABLE retrieval_trace FIELDS agent_id;
DEFINE INDEX trace_session_idx ON TABLE retrieval_trace FIELDS session_id;

-- ---------------------------------------------------------------------------
-- 4. DECISION TRACE — audit trail
-- ---------------------------------------------------------------------------

DEFINE TABLE decision_trace SCHEMAFULL;

DEFINE FIELD run_id      ON TABLE decision_trace TYPE string;
DEFINE FIELD step_id     ON TABLE decision_trace TYPE string;
DEFINE FIELD agent_id    ON TABLE decision_trace TYPE string;
DEFINE FIELD actor       ON TABLE decision_trace TYPE option<string>;
DEFINE FIELD action      ON TABLE decision_trace TYPE string;
DEFINE FIELD input       ON TABLE decision_trace TYPE object FLEXIBLE;
DEFINE FIELD output      ON TABLE decision_trace TYPE object FLEXIBLE;
DEFINE FIELD status      ON TABLE decision_trace TYPE string
    ASSERT $value IN ['pending','success','failed','rejected'];
DEFINE FIELD memory_refs ON TABLE decision_trace TYPE option<array<record<memory>>>;
DEFINE FIELD created_at  ON TABLE decision_trace TYPE datetime VALUE time::now();

DEFINE INDEX dt_run_idx   ON TABLE decision_trace FIELDS run_id;
DEFINE INDEX dt_agent_idx ON TABLE decision_trace FIELDS agent_id;

-- ---------------------------------------------------------------------------
-- 5. WORKING MEMORY — Cortex layers (Spacebot pattern)
-- Never written per LLM call. Background-synthesised.
-- ---------------------------------------------------------------------------

DEFINE TABLE working_memory SCHEMAFULL;

DEFINE FIELD agent_id        ON TABLE working_memory TYPE string;
DEFINE FIELD layer           ON TABLE working_memory TYPE string
    ASSERT $value IN ['identity_context','intraday_synthesis','daily_rollup','cross_agent_map','knowledge_brief'];
DEFINE FIELD content         ON TABLE working_memory TYPE string;
DEFINE FIELD source_memories ON TABLE working_memory TYPE option<array<record<memory>>>;
DEFINE FIELD valid_date      ON TABLE working_memory TYPE option<datetime>;
DEFINE FIELD token_count     ON TABLE working_memory TYPE option<int>;
DEFINE FIELD created_at      ON TABLE working_memory TYPE datetime VALUE time::now();
DEFINE FIELD updated_at      ON TABLE working_memory TYPE datetime VALUE time::now();

DEFINE INDEX wm_agent_layer_idx ON TABLE working_memory FIELDS agent_id, layer UNIQUE;

-- ---------------------------------------------------------------------------
-- 6. EVOLUTION QUEUE — A-Mem: fired by DEFINE EVENT on every INSERT
-- ---------------------------------------------------------------------------

DEFINE TABLE evolution_queue SCHEMAFULL;

DEFINE FIELD new_memory_id ON TABLE evolution_queue TYPE record<memory>;
DEFINE FIELD agent_id      ON TABLE evolution_queue TYPE string;
DEFINE FIELD category      ON TABLE evolution_queue TYPE string;
DEFINE FIELD status        ON TABLE evolution_queue TYPE string DEFAULT 'pending'
    ASSERT $value IN ['pending','processing','done','skipped'];
DEFINE FIELD processed_at  ON TABLE evolution_queue TYPE option<datetime>;
DEFINE FIELD created_at    ON TABLE evolution_queue TYPE datetime VALUE time::now();

DEFINE INDEX eq_status_idx ON TABLE evolution_queue FIELDS status;
DEFINE INDEX eq_agent_idx  ON TABLE evolution_queue FIELDS agent_id;

-- ---------------------------------------------------------------------------
-- 7. EVENT: queue evolution job on every new memory
-- ---------------------------------------------------------------------------

DEFINE EVENT memory_created ON TABLE memory
    WHEN $event = "CREATE"
    THEN {
        CREATE evolution_queue SET
            new_memory_id = $value.id,
            agent_id      = $value.agent_id,
            category      = $value.category,
            status        = 'pending',
            created_at    = time::now()
    };
