use anyhow::Result;
use chrono::Utc;
use surrealdb::types::{RecordId, SurrealValue};
use tracing::{info, warn};

use crate::memory::{
    decay::effective_confidence,
    store::Store,
    types::*,
};

// ---------------------------------------------------------------------------
// Conflict types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
pub enum ConflictType {
    /// Agent stored an interpretation, human says it was wrong.
    /// Accept. Version the interpretation. Log what was misread.
    Misinterpretation,

    /// Human says agent said/recorded X. Agent's log says Y.
    /// Stand firm. Show the exact log. Offer new decision only.
    AgentStandsFirm,

    /// Human claims a number or verifiable fact differs from chat log.
    /// Show exact line. Stop that reasoning thread. Do not negotiate.
    FactualContradiction,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Resolution {
    /// New interpretation version created. Continue normally.
    ResolvedMisinterpretation,

    /// Agent showed its log, stood firm. Human can make a new decision.
    AgentHoldsRecord,

    /// Agent stopped. Factual contradiction. Reasoning halted on this thread.
    HaltReasoning,

    /// Genuinely unclear. Human decides.
    DeferredToHuman,
}

// ---------------------------------------------------------------------------
// ConflictTrace — what gets stored and what gets returned to the agent
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ConflictTrace {
    pub id:                        Option<RecordId>,
    pub agent_id:                  String,
    pub session_id:                Option<String>,
    pub conflict_type:             ConflictType,

    // What the agent had
    pub prior_memory_id:           Option<RecordId>,
    pub prior_content:             Option<String>,
    pub prior_confidence:          Option<f64>,
    pub prior_effective_confidence: Option<f64>,
    pub prior_source_kind:         Option<SourceKind>,
    pub prior_known_time:          Option<chrono::DateTime<Utc>>,
    pub prior_epistemic_status:    Option<EpistemicStatus>,
    pub prior_verbatim:            Option<String>,

    // What the human said
    pub human_statement:           String,
    pub human_source_trust:        f64,

    // Resolution
    pub resolution:                Resolution,
    pub resolved_memory_id:        Option<RecordId>,
    pub interpretation_version:    Option<i64>,
    pub calibration_reasoning:     Option<String>,

    // What the agent should say
    pub agent_response:            String,

    // Whether downstream reasoning should halt
    pub halt_reasoning:            bool,
}

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct ConflictInput {
    pub agent_id:         String,
    pub session_id:       Option<String>,
    pub conflict_type:    ConflictType,
    pub human_statement:  String,
    /// The memory the human is contradicting / correcting
    pub prior_memory_id:  Option<String>,
    /// For misinterpretation: what the correct interpretation should be
    pub correct_interpretation: Option<String>,
}

// ---------------------------------------------------------------------------
// ConflictResolver
// ---------------------------------------------------------------------------

pub struct ConflictResolver<'a> {
    store: &'a Store,
}

impl<'a> ConflictResolver<'a> {
    pub fn new(store: &'a Store) -> Self {
        Self { store }
    }

    pub async fn resolve(&self, input: ConflictInput) -> Result<ConflictTrace> {
        match input.conflict_type {
            ConflictType::Misinterpretation => {
                self.resolve_misinterpretation(input).await
            }
            ConflictType::AgentStandsFirm => {
                self.resolve_stand_firm(input).await
            }
            ConflictType::FactualContradiction => {
                self.resolve_factual_contradiction(input).await
            }
        }
    }

    // -----------------------------------------------------------------------
    // Misinterpretation
    // "No, when I said X I meant Y"
    //
    // Agent does not argue about what the human said.
    // Agent accepts the interpretation was wrong.
    // Supersedes the stored interpretation with the correct one.
    // Versions are linked via derived_from → same original episodic turn.
    // -----------------------------------------------------------------------

    async fn resolve_misinterpretation(
        &self,
        input: ConflictInput,
    ) -> Result<ConflictTrace> {
        let now = Utc::now();
        let mut prior_content = None;
        let mut prior_confidence = None;
        let mut prior_effective = None;
        let mut prior_source_kind = None;
        let mut prior_known_time = None;
        let mut prior_epistemic = None;
        let mut prior_id: Option<RecordId> = None;
        let mut interpretation_version: i64 = 1;
        let mut resolved_memory_id: Option<RecordId> = None;

        // Fetch prior memory
        if let Some(ref mid) = input.prior_memory_id {
            if let Some(prior) = self.store.select_memory(mid).await? {
                prior_id = prior.id.clone();
                prior_content = Some(prior.content.clone());
                prior_confidence = Some(prior.confidence);
                prior_effective = Some(effective_confidence(&prior, now));
                prior_source_kind = Some(prior.source_kind.clone());
                prior_known_time = prior.known_time;
                prior_epistemic = Some(prior.epistemic_status.clone());

                // Count existing versions to set new version number
                let lineage = self.store.supersession_lineage(mid).await?;
                interpretation_version = lineage.len() as i64 + 1;

                // Create new interpretation version
                if let Some(ref correct) = input.correct_interpretation {
                    // Preserve derived_from — links back to original episodic turn
                    let derived = prior.derived_from.clone()
                        .unwrap_or_default();

                    let new_mem = self.store.create_memory(MemoryInput {
                        agent_id:        input.agent_id.clone(),
                        content:         correct.clone(),
                        category:        prior.category.clone(),
                        session_id:      input.session_id.clone(),
                        scope:           Some(prior.scope.clone()),
                        source_kind:     Some(SourceKind::UserTurn),
                        source_trust:    Some(0.92),
                        confidence:      Some(0.90),
                        importance:      Some(prior.importance),
                        epistemic_status: Some(EpistemicStatus::Belief),
                        derived_from:    Some(
                            derived.iter()
                                .map(|r| r.key_str())
                                .chain(std::iter::once(mid.clone()))
                                .collect()
                        ),
                        summary:         None,
                        valid_time_start: None,
                        valid_time_end:   None,
                        source_ref:      None,
                        keywords:        prior.keywords.clone(),
                        tags:            prior.tags.clone(),
                        embedding:       None,
                        decay_lambda:    None,
                    }).await?;

                    resolved_memory_id = new_mem.id.clone();

                    // Supersede the prior interpretation
                    self.store.forget(mid).await?;

                    info!(
                        "misinterpretation resolved: {} → {} (v{})",
                        mid,
                        new_mem.id.as_ref().map(|i| i.key_str()).unwrap_or_default(),
                        interpretation_version
                    );
                }
            }
        }

        let agent_response = build_misinterpretation_response(
            prior_content.as_deref(),
            input.correct_interpretation.as_deref(),
            interpretation_version,
        );

        let trace = ConflictTrace {
            id: None,
            agent_id: input.agent_id,
            session_id: input.session_id,
            conflict_type: ConflictType::Misinterpretation,
            prior_memory_id: prior_id,
            prior_content,
            prior_confidence,
            prior_effective_confidence: prior_effective,
            prior_source_kind,
            prior_known_time,
            prior_epistemic_status: prior_epistemic,
            prior_verbatim: None,
            human_statement: input.human_statement,
            human_source_trust: 0.92,
            resolution: Resolution::ResolvedMisinterpretation,
            resolved_memory_id,
            interpretation_version: Some(interpretation_version),
            calibration_reasoning: Some(format!(
                "Human corrected interpretation. Agent accepted. \
                 Interpretation versioned to v{}.",
                interpretation_version
            )),
            agent_response: agent_response.clone(),
            halt_reasoning: false,
        };

        self.store.create_conflict_trace(&trace).await?;
        Ok(trace)
    }

    // -----------------------------------------------------------------------
    // Agent stands firm
    // "You told me X" — but the log says Y
    //
    // Agent retrieves the exact episodic memory.
    // Shows verbatim content, timestamp, session.
    // Does not update anything.
    // Offers: "if you want to make a new decision, I'll record that."
    // -----------------------------------------------------------------------

    async fn resolve_stand_firm(
        &self,
        input: ConflictInput,
    ) -> Result<ConflictTrace> {
        let now = Utc::now();
        let mut prior_content = None;
        let mut prior_confidence = None;
        let mut prior_effective = None;
        let mut prior_source_kind = None;
        let mut prior_known_time = None;
        let mut prior_epistemic = None;
        let mut prior_id: Option<RecordId> = None;
        let mut prior_verbatim = None;

        if let Some(ref mid) = input.prior_memory_id {
            if let Some(prior) = self.store.select_memory(mid).await? {
                prior_id = prior.id.clone();
                prior_verbatim = Some(prior.content.clone());
                prior_content = Some(prior.content.clone());
                prior_confidence = Some(prior.confidence);
                prior_effective = Some(effective_confidence(&prior, now));
                prior_source_kind = Some(prior.source_kind.clone());
                prior_known_time = prior.known_time;
                prior_epistemic = Some(prior.epistemic_status.clone());
            }
        }

        let agent_response = build_stand_firm_response(
            prior_verbatim.as_deref(),
            prior_known_time,
            &input.session_id,
        );

        warn!(
            "agent stands firm: human='{}' | record='{}'",
            input.human_statement,
            prior_verbatim.as_deref().unwrap_or("(no prior found)")
        );

        let trace = ConflictTrace {
            id: None,
            agent_id: input.agent_id,
            session_id: input.session_id,
            conflict_type: ConflictType::AgentStandsFirm,
            prior_memory_id: prior_id,
            prior_content,
            prior_confidence,
            prior_effective_confidence: prior_effective,
            prior_source_kind,
            prior_known_time,
            prior_epistemic_status: prior_epistemic,
            prior_verbatim,
            human_statement: input.human_statement,
            human_source_trust: 0.9,
            resolution: Resolution::AgentHoldsRecord,
            resolved_memory_id: None,
            interpretation_version: None,
            calibration_reasoning: Some(
                "Human disputed what agent said/recorded. \
                 Agent retrieved exact log and showed it. \
                 Record is immutable. New decision offered."
                    .to_string(),
            ),
            agent_response: agent_response.clone(),
            halt_reasoning: false,
        };

        self.store.create_conflict_trace(&trace).await?;
        Ok(trace)
    }

    // -----------------------------------------------------------------------
    // Factual contradiction
    // "I said the budget was $50,000" — but the log says $5,000
    //
    // Agent shows the exact line from the chat log.
    // Sets halt_reasoning = true.
    // Does not continue processing downstream from the contested fact.
    // Does not negotiate. Does not update.
    // -----------------------------------------------------------------------

    async fn resolve_factual_contradiction(
        &self,
        input: ConflictInput,
    ) -> Result<ConflictTrace> {
        let mut prior_content = None;
        let mut prior_source_kind = None;
        let mut prior_known_time = None;
        let mut prior_id: Option<RecordId> = None;
        let mut prior_verbatim = None;

        if let Some(ref mid) = input.prior_memory_id {
            if let Some(prior) = self.store.select_memory(mid).await? {
                prior_id = prior.id.clone();
                prior_verbatim = Some(prior.content.clone());
                prior_content = Some(prior.content.clone());
                prior_source_kind = Some(prior.source_kind.clone());
                prior_known_time = prior.known_time;
            }
        }

        let agent_response = build_factual_contradiction_response(
            prior_verbatim.as_deref(),
            prior_known_time,
            &input.session_id,
        );

        warn!(
            "factual contradiction — halting reasoning thread: \
             human='{}' | record='{}'",
            input.human_statement,
            prior_verbatim.as_deref().unwrap_or("(no prior found)")
        );

        let trace = ConflictTrace {
            id: None,
            agent_id: input.agent_id,
            session_id: input.session_id,
            conflict_type: ConflictType::FactualContradiction,
            prior_memory_id: prior_id,
            prior_content,
            prior_confidence: Some(1.0), // episodic = immutable = max confidence
            prior_effective_confidence: Some(1.0),
            prior_source_kind,
            prior_known_time,
            prior_epistemic_status: Some(EpistemicStatus::Fact),
            prior_verbatim,
            human_statement: input.human_statement,
            human_source_trust: 0.9,
            resolution: Resolution::HaltReasoning,
            resolved_memory_id: None,
            interpretation_version: None,
            calibration_reasoning: Some(
                "Human contradicted a verifiable fact in the chat log. \
                 Episodic records are immutable. \
                 Reasoning halted on this thread. \
                 Human may make a new decision to proceed with different values."
                    .to_string(),
            ),
            agent_response: agent_response.clone(),
            halt_reasoning: true,
        };

        self.store.create_conflict_trace(&trace).await?;
        Ok(trace)
    }
}

// ---------------------------------------------------------------------------
// Response builders — what the agent actually says
// These are templates. Agent runtime may use them directly or incorporate
// them into a larger response. They are honest, firm, and not hostile.
// ---------------------------------------------------------------------------

fn build_misinterpretation_response(
    prior: Option<&str>,
    correct: Option<&str>,
    version: i64,
) -> String {
    match (prior, correct) {
        (Some(p), Some(c)) => format!(
            "I had stored that as \"{}\" — but I got the interpretation wrong. \
             What you meant was \"{}\". I've updated that (version {}). \
             The original conversation is still in the record.",
            p, c, version
        ),
        (Some(p), None) => format!(
            "I had stored that as \"{}\". \
             If that's not what you meant, tell me what you did mean \
             and I'll update my understanding.",
            p
        ),
        _ => "I may have misread that. Tell me what you meant \
              and I'll correct my understanding."
            .to_string(),
    }
}

fn build_stand_firm_response(
    verbatim: Option<&str>,
    known_time: Option<chrono::DateTime<Utc>>,
    session_id: &Option<String>,
) -> String {
    let time_str = known_time
        .map(|t| t.format("%Y-%m-%d %H:%M UTC").to_string())
        .unwrap_or_else(|| "unknown time".to_string());

    let session_str = session_id
        .as_deref()
        .map(|s| format!(", session {}", s))
        .unwrap_or_default();

    match verbatim {
        Some(v) => format!(
            "My record shows: \"{}\" — logged at {}{}.  \
             That is what I have. I can't proceed as if something \
             different was said. If you want to make a new decision, \
             tell me and I'll record that as a new entry.",
            v, time_str, session_str
        ),
        None => "I don't have a record of that being said at all. \
                 If you believe it was, I may have missed storing it. \
                 Tell me what was said and I'll record it now."
            .to_string(),
    }
}

fn build_factual_contradiction_response(
    verbatim: Option<&str>,
    known_time: Option<chrono::DateTime<Utc>>,
    session_id: &Option<String>,
) -> String {
    let time_str = known_time
        .map(|t| t.format("%Y-%m-%d %H:%M UTC").to_string())
        .unwrap_or_else(|| "unknown time".to_string());

    let session_str = session_id
        .as_deref()
        .map(|s| format!(", session {}", s))
        .unwrap_or_default();

    match verbatim {
        Some(v) => format!(
            "The chat log shows: \"{}\" — recorded at {}{}.  \
             I can't continue on the basis that a different value was stated \
             when the record is clear. \
             If the number has changed, that's a new decision — \
             tell me and I'll record it. But I won't treat the record \
             as if it said something it didn't.",
            v, time_str, session_str
        ),
        None => "I don't have that in the record. \
                 If you're confident it was said, I may have a gap. \
                 I can't continue reasoning from a value I have no record of."
            .to_string(),
    }
}

// ---------------------------------------------------------------------------
// Store extension — create_conflict_trace
// Lives here, called from ConflictResolver
// Implemented on Store via store_gap.rs pattern
// ---------------------------------------------------------------------------

impl Store {
    pub async fn create_conflict_trace(&self, ct: &ConflictTrace) -> Result<()> {
        let conflict_type_str = match ct.conflict_type {
            ConflictType::Misinterpretation    => "misinterpretation",
            ConflictType::AgentStandsFirm      => "agent_stands_firm",
            ConflictType::FactualContradiction => "factual_contradiction",
        };
        let resolution_str = match ct.resolution {
            Resolution::ResolvedMisinterpretation => "resolved_misinterpretation",
            Resolution::AgentHoldsRecord          => "agent_holds_record",
            Resolution::HaltReasoning             => "halt_reasoning",
            Resolution::DeferredToHuman           => "deferred_to_human",
        };
        let source_kind_str = ct.prior_source_kind.as_ref()
            .map(|s| serde_json::to_value(s).unwrap_or_default());
        let epistemic_str = ct.prior_epistemic_status.as_ref()
            .map(|s| serde_json::to_value(s).unwrap_or_default());
        let decided_by = if ct.halt_reasoning { "agent_calibration" } else { "agent_calibration" };

        self.db.query(
            r#"
            CREATE conflict_trace SET
                agent_id                   = $agent_id,
                session_id                 = $session_id,
                conflict_type              = $conflict_type,
                prior_memory_id            = $prior_memory_id,
                prior_content              = $prior_content,
                prior_confidence           = $prior_confidence,
                prior_effective_confidence = $prior_effective_confidence,
                prior_source_kind          = $prior_source_kind,
                prior_known_time           = $prior_known_time,
                prior_epistemic_status     = $prior_epistemic_status,
                prior_verbatim             = $prior_verbatim,
                human_statement            = $human_statement,
                human_source_trust         = $human_source_trust,
                resolution                 = $resolution,
                resolved_memory_id         = $resolved_memory_id,
                interpretation_version     = $interpretation_version,
                calibration_reasoning      = $calibration_reasoning,
                agent_response             = $agent_response,
                halt_reasoning             = $halt_reasoning,
                decided_by                 = $decided_by,
                created_at                 = time::now();
            "#,
        )
        .bind(("agent_id",                   ct.agent_id.clone()))
        .bind(("session_id",                 ct.session_id.clone()))
        .bind(("conflict_type",              conflict_type_str))
        .bind(("prior_memory_id",            ct.prior_memory_id.clone()))
        .bind(("prior_content",              ct.prior_content.clone()))
        .bind(("prior_confidence",           ct.prior_confidence))
        .bind(("prior_effective_confidence", ct.prior_effective_confidence))
        .bind(("prior_source_kind",          source_kind_str))
        .bind(("prior_known_time",           ct.prior_known_time))
        .bind(("prior_epistemic_status",     epistemic_str))
        .bind(("prior_verbatim",             ct.prior_verbatim.clone()))
        .bind(("human_statement",            ct.human_statement.clone()))
        .bind(("human_source_trust",         ct.human_source_trust))
        .bind(("resolution",                 resolution_str))
        .bind(("resolved_memory_id",         ct.resolved_memory_id.clone()))
        .bind(("interpretation_version",     ct.interpretation_version))
        .bind(("calibration_reasoning",      ct.calibration_reasoning.clone()))
        .bind(("agent_response",             ct.agent_response.clone()))
        .bind(("halt_reasoning",             ct.halt_reasoning))
        .bind(("decided_by",                 decided_by))
        .await?;

        Ok(())
    }

    /// Fetch recent conflict traces for an agent — for decision log display.
    pub async fn conflict_history(
        &self,
        agent_id: &str,
        limit: usize,
    ) -> Result<Vec<ConflictTraceRow>> {
        let mut res = self.db.query(
            r#"
            SELECT * FROM conflict_trace
            WHERE agent_id = $agent_id
            ORDER BY created_at DESC
            LIMIT $limit;
            "#,
        )
        .bind(("agent_id", agent_id.to_string()))
        .bind(("limit",    limit as i64))
        .await?;

        let rows: Vec<ConflictTraceRow> = res.take(0)?;
        Ok(rows)
    }
}

/// Flat row returned from DB for display
#[derive(Debug, Clone, serde::Deserialize, surrealdb::types::SurrealValue)]
pub struct ConflictTraceRow {
    pub id:                    Option<RecordId>,
    pub agent_id:              String,
    pub conflict_type:         String,
    pub prior_content:         Option<String>,
    pub prior_verbatim:        Option<String>,
    pub prior_known_time:      Option<chrono::DateTime<Utc>>,
    pub human_statement:       String,
    pub resolution:            String,
    pub calibration_reasoning: Option<String>,
    pub agent_response:        Option<String>,
    pub halt_reasoning:        bool,
    pub created_at:            Option<chrono::DateTime<Utc>>,
}
