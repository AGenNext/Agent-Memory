-- =============================================================================
-- Agent-Memory v0.2 — Human memory behaviour
-- Applied at binary boot (idempotent — DEFINE is safe to re-run)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Additions to existing memory table
--
-- epistemic_status: fact | belief | assumption | hearsay | inferred
--   fact       → externally verifiable, does not decay
--   belief     → held as true, decays with time
--   assumption → agent inferred this, not stated explicitly
--   hearsay    → "user said X told them Y" — low trust
--   inferred   → derived by elaboration or consolidation
--
-- last_reinforced_at: reset every time memory is recalled and marked useful
-- reinforcement_count: how many times this memory has been successfully used
-- decay_lambda: category-specific decay rate for Ebbinghaus curve
--   episodic    → 0.10 (decays fast, context specific)
--   knowledge   → 0.02 (medium)
--   context     → 0.50 (very fast, current session only)
--   identity    → 0.001 (very slow, stable)
--   instruction → 0.0   (does not decay)
--   uncertainty → 0.03  (medium)
--   fact        → 0.0   (does not decay)
-- ---------------------------------------------------------------------------

DEFINE FIELD epistemic_status    ON TABLE memory TYPE string DEFAULT 'belief'
    ASSERT $value IN ['fact','belief','assumption','hearsay','inferred'];
DEFINE FIELD last_reinforced_at  ON TABLE memory TYPE option<datetime>;
DEFINE FIELD reinforcement_count ON TABLE memory TYPE int DEFAULT 0;
DEFINE FIELD decay_lambda        ON TABLE memory TYPE float DEFAULT 0.02;

-- Index for decay-aware recall (find recently reinforced memories)
DEFINE INDEX memory_reinforced_idx ON TABLE memory FIELDS agent_id, last_reinforced_at;

-- ---------------------------------------------------------------------------
-- GAP PROBE — records every failed search with full metadata
--
-- When escalating_recall() exhausts all four tiers and finds nothing,
-- a gap_probe is written. This is information — the agent knows it has a gap.
-- The human's insistence becomes a signal, not just an awkward moment.
-- ---------------------------------------------------------------------------

DEFINE TABLE gap_probe SCHEMAFULL;

DEFINE FIELD agent_id        ON TABLE gap_probe TYPE string;
DEFINE FIELD session_id      ON TABLE gap_probe TYPE option<string>;
DEFINE FIELD query_text      ON TABLE gap_probe TYPE string;
-- What the human said that triggered the gap search
DEFINE FIELD human_insistence ON TABLE gap_probe TYPE option<string>;
-- Tiers tried before giving up (1,2,3,4)
DEFINE FIELD tiers_tried     ON TABLE gap_probe TYPE array<int>;
-- Whether we also searched superseded memories
DEFINE FIELD searched_superseded ON TABLE gap_probe TYPE bool DEFAULT false;
-- Whether we tried temporal expansion (past time windows)
DEFINE FIELD searched_temporal   ON TABLE gap_probe TYPE bool DEFAULT false;
-- Whether we tried scope relaxation (session → agent → team)
DEFINE FIELD searched_wider_scope ON TABLE gap_probe TYPE bool DEFAULT false;
-- Anchor hint provided by human to help locate the memory
DEFINE FIELD anchor_hint     ON TABLE gap_probe TYPE option<string>;
-- Which session was replayed to resolve this gap (if any)
DEFINE FIELD resolved_by_session ON TABLE gap_probe TYPE option<string>;
-- Was this gap eventually resolved?
DEFINE FIELD resolved        ON TABLE gap_probe TYPE bool DEFAULT false;
DEFINE FIELD resolved_at     ON TABLE gap_probe TYPE option<datetime>;
-- What was learned when resolved
DEFINE FIELD resolution_memory_id ON TABLE gap_probe TYPE option<record<memory>>;

DEFINE FIELD created_at      ON TABLE gap_probe TYPE datetime VALUE time::now();

DEFINE INDEX gap_agent_idx      ON TABLE gap_probe FIELDS agent_id;
DEFINE INDEX gap_session_idx    ON TABLE gap_probe FIELDS session_id;
DEFINE INDEX gap_resolved_idx   ON TABLE gap_probe FIELDS agent_id, resolved;

-- ---------------------------------------------------------------------------
-- SESSION INDEX — maps session_id → time window + summary
--
-- Every episodic memory already has session_id.
-- This table lets us quickly find which sessions overlap a time window
-- without scanning all episodic memories.
-- Built by store::record_session_bounds() on every episodic write.
-- ---------------------------------------------------------------------------

DEFINE TABLE session_index SCHEMAFULL;

DEFINE FIELD session_id   ON TABLE session_index TYPE string;
DEFINE FIELD agent_id     ON TABLE session_index TYPE string;
-- Earliest known_time of any memory in this session
DEFINE FIELD started_at   ON TABLE session_index TYPE datetime;
-- Latest known_time of any memory in this session
DEFINE FIELD ended_at     ON TABLE session_index TYPE datetime;
-- Short summary of what this session was about (from intraday synthesis)
DEFINE FIELD summary      ON TABLE session_index TYPE option<string>;
-- Topics / keywords extracted from this session
DEFINE FIELD topics       ON TABLE session_index TYPE option<array<string>>;
DEFINE FIELD memory_count ON TABLE session_index TYPE int DEFAULT 0;
DEFINE FIELD updated_at   ON TABLE session_index TYPE datetime VALUE time::now();

DEFINE INDEX si_agent_idx    ON TABLE session_index FIELDS agent_id;
DEFINE INDEX si_session_idx  ON TABLE session_index FIELDS session_id UNIQUE;
DEFINE INDEX si_time_idx     ON TABLE session_index FIELDS agent_id, started_at, ended_at;

-- ---------------------------------------------------------------------------
-- ACTIVE EPISODE — loaded into working memory when a session is replayed
--
-- This is the "context flood" — when the human provides a time anchor
-- and the agent replays a complete past session into active working memory.
-- Short-lived: cleared when current session ends.
-- One row per agent at most.
-- ---------------------------------------------------------------------------

DEFINE TABLE active_episode SCHEMAFULL;

DEFINE FIELD agent_id         ON TABLE active_episode TYPE string;
DEFINE FIELD replayed_session ON TABLE active_episode TYPE string;
DEFINE FIELD started_at       ON TABLE active_episode TYPE datetime;
DEFINE FIELD ended_at         ON TABLE active_episode TYPE datetime;
-- All memories from the replayed session, ordered by known_time
DEFINE FIELD memories         ON TABLE active_episode TYPE array<record<memory>>;
-- Reconstructed conversation thread as text for prompt injection
DEFINE FIELD thread_text      ON TABLE active_episode TYPE string;
DEFINE FIELD token_count      ON TABLE active_episode TYPE int DEFAULT 0;
-- The gap probe this replay was triggered by
DEFINE FIELD gap_probe_id     ON TABLE active_episode TYPE option<record<gap_probe>>;
DEFINE FIELD created_at       ON TABLE active_episode TYPE datetime VALUE time::now();
DEFINE FIELD updated_at       ON TABLE active_episode TYPE datetime VALUE time::now();

DEFINE INDEX ae_agent_idx ON TABLE active_episode FIELDS agent_id UNIQUE;

-- ---------------------------------------------------------------------------
-- Add active_episode to working_memory layer enum
-- (DEFINE FIELD is idempotent — re-running updates the ASSERT)
-- ---------------------------------------------------------------------------

DEFINE FIELD layer ON TABLE working_memory TYPE string
    ASSERT $value IN [
        'identity_context',
        'intraday_synthesis',
        'daily_rollup',
        'cross_agent_map',
        'knowledge_brief',
        'active_episode'
    ];
