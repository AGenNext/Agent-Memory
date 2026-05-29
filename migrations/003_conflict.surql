-- =============================================================================
-- Agent-Memory v0.3 — Conflict resolution
-- Applied at binary boot (idempotent)
-- =============================================================================

-- ---------------------------------------------------------------------------
-- CONFLICT TRACE — first-class record of every conflict resolution
--
-- Every conflict between what the agent has and what the human says
-- is recorded here. This is the decision log the agent can surface
-- to the human and reference in future reasoning.
--
-- conflict_type:
--   misinterpretation   agent stored an interpretation, human says it was wrong
--                       → accept, version the interpretation, log what was misread
--   agent_stands_firm   human says agent said/recorded X, agent's log says Y
--                       → show exact log, do not update, offer new decision only
--   factual_contradiction human claims a number/fact differs from chat log
--                       → show exact line, stop that reasoning thread
--
-- resolution:
--   resolved_misinterpretation  new interpretation version created
--   agent_holds_record          agent showed its log, stood firm
--   halt_reasoning              agent stopped — factual contradiction
--   deferred_to_human           genuinely unclear, human decides
-- ---------------------------------------------------------------------------

DEFINE TABLE conflict_trace SCHEMAFULL;

DEFINE FIELD agent_id          ON TABLE conflict_trace TYPE string;
DEFINE FIELD session_id        ON TABLE conflict_trace TYPE option<string>;

-- Conflict classification
DEFINE FIELD conflict_type     ON TABLE conflict_trace TYPE string
    ASSERT $value IN [
        'misinterpretation',
        'agent_stands_firm',
        'factual_contradiction'
    ];

-- What the agent had
DEFINE FIELD prior_memory_id   ON TABLE conflict_trace TYPE option<record<memory>>;
DEFINE FIELD prior_content     ON TABLE conflict_trace TYPE option<string>;
DEFINE FIELD prior_confidence  ON TABLE conflict_trace TYPE option<float>;
DEFINE FIELD prior_effective_confidence ON TABLE conflict_trace TYPE option<float>;
DEFINE FIELD prior_source_kind ON TABLE conflict_trace TYPE option<string>;
DEFINE FIELD prior_known_time  ON TABLE conflict_trace TYPE option<datetime>;
DEFINE FIELD prior_epistemic_status ON TABLE conflict_trace TYPE option<string>;
-- For episodic/factual: the exact verbatim text from the chat log
DEFINE FIELD prior_verbatim    ON TABLE conflict_trace TYPE option<string>;

-- What the human said this turn
DEFINE FIELD human_statement   ON TABLE conflict_trace TYPE string;
DEFINE FIELD human_source_trust ON TABLE conflict_trace TYPE float DEFAULT 0.9;

-- Resolution
DEFINE FIELD resolution        ON TABLE conflict_trace TYPE string
    ASSERT $value IN [
        'resolved_misinterpretation',
        'agent_holds_record',
        'halt_reasoning',
        'deferred_to_human'
    ];

-- New memory created (if interpretation was versioned)
DEFINE FIELD resolved_memory_id ON TABLE conflict_trace TYPE option<record<memory>>;

-- The interpretation version number (v1, v2, v3...)
DEFINE FIELD interpretation_version ON TABLE conflict_trace TYPE option<int>;

-- Visible calibration reasoning — stored so agent can show it
-- e.g. "Prior belief confidence 0.65 (decayed from 0.85 over 21 days).
--       Human direct statement trust: 0.90. Human wins."
DEFINE FIELD calibration_reasoning ON TABLE conflict_trace TYPE option<string>;

-- The exact text the agent said to the human about this conflict
DEFINE FIELD agent_response    ON TABLE conflict_trace TYPE option<string>;

-- Whether this halted downstream reasoning
DEFINE FIELD halt_reasoning    ON TABLE conflict_trace TYPE bool DEFAULT false;

-- Who resolved it
DEFINE FIELD decided_by        ON TABLE conflict_trace TYPE string DEFAULT 'agent_calibration'
    ASSERT $value IN ['agent_calibration', 'human_override', 'deferred'];

DEFINE FIELD created_at        ON TABLE conflict_trace TYPE datetime VALUE time::now();

DEFINE INDEX ct_agent_idx      ON TABLE conflict_trace FIELDS agent_id;
DEFINE INDEX ct_session_idx    ON TABLE conflict_trace FIELDS session_id;
DEFINE INDEX ct_type_idx       ON TABLE conflict_trace FIELDS agent_id, conflict_type;
