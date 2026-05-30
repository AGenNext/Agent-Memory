#![deny(clippy::all)]

use napi::bindgen_prelude::*;
use napi_derive::napi;
use std::sync::Arc;
use tokio::sync::Mutex;

// Re-use the Rust library
use agent_memory::{
    AgentMemory as CoreMemory,
    ConflictInput,
    ConflictType,
    MemoryCategory,
    MemoryInput,
    RecallQuery,
    RetrievalTier,
    SourceKind,
    EpistemicStatus,
    SupersedeInput,
    RecordIdExt,
};

// ---------------------------------------------------------------------------
// AgentMemory — the Node.js class
// ---------------------------------------------------------------------------

#[napi]
pub struct AgentMemory {
    inner: Arc<Mutex<CoreMemory>>,
}

#[napi]
impl AgentMemory {
    /// Open persistent memory at data_dir.
    #[napi(factory)]
    pub async fn open(data_dir: String) -> Result<Self> {
        let core = CoreMemory::open(&data_dir)
            .await
            .map_err(|e| Error::from_reason(e.to_string()))?;
        Ok(Self { inner: Arc::new(Mutex::new(core)) })
    }

    /// Open ephemeral in-memory store (for testing).
    #[napi(factory)]
    pub async fn open_mem() -> Result<Self> {
        let core = CoreMemory::open_mem()
            .await
            .map_err(|e| Error::from_reason(e.to_string()))?;
        Ok(Self { inner: Arc::new(Mutex::new(core)) })
    }

    /// Store a new memory.
    #[napi]
    pub async fn remember(&self, input: JsMemoryInput) -> Result<JsMemory> {
        let core = self.inner.lock().await;
        let result = core.remember(input.into())
            .await
            .map_err(|e| Error::from_reason(e.to_string()))?;
        Ok(JsMemory::from(result))
    }

    /// Retrieve memories using hybrid search.
    #[napi]
    pub async fn recall(&self, input: JsRecallQuery) -> Result<JsRecallResult> {
        let core = self.inner.lock().await;
        let result = core.recall(input.into())
            .await
            .map_err(|e| Error::from_reason(e.to_string()))?;
        Ok(JsRecallResult::from(result))
    }

    /// Recall with full escalation — tries all tiers before returning a gap probe.
    #[napi]
    pub async fn recall_or_gap(
        &self,
        input:            JsRecallQuery,
        human_insistence: Option<String>,
    ) -> Result<JsRecallOutcome> {
        let core = self.inner.lock().await;
        let result = core.recall_or_gap(input.into(), human_insistence)
            .await
            .map_err(|e| Error::from_reason(e.to_string()))?;
        Ok(JsRecallOutcome::from(result))
    }

    /// Supersede a memory — old record preserved, new record created.
    #[napi]
    pub async fn update(
        &self,
        old_memory_id: String,
        new_content:   String,
        confidence:    Option<f64>,
    ) -> Result<JsUpdateResult> {
        let core = self.inner.lock().await;
        let input = SupersedeInput {
            old_memory_id,
            new_content,
            confidence,
            source_kind: None,
            source_ref:  None,
            embedding:   None,
        };
        let (old, new) = core.update(input)
            .await
            .map_err(|e| Error::from_reason(e.to_string()))?;
        Ok(JsUpdateResult {
            superseded: JsMemory::from(old),
            new:        JsMemory::from(new),
        })
    }

    /// Soft-forget a memory.
    #[napi]
    pub async fn forget(&self, memory_id: String) -> Result<()> {
        let core = self.inner.lock().await;
        core.forget(&memory_id)
            .await
            .map_err(|e| Error::from_reason(e.to_string()))
    }

    /// Reinforce memories — resets their decay.
    #[napi]
    pub async fn reinforce(&self, memory_ids: Vec<String>) -> Result<()> {
        let core = self.inner.lock().await;
        core.reinforce(&memory_ids)
            .await
            .map_err(|e| Error::from_reason(e.to_string()))
    }

    /// Resolve a conflict.
    /// conflict_type: "misinterpretation" | "agent_stands_firm" | "factual_contradiction"
    #[napi]
    pub async fn resolve_conflict(
        &self,
        agent_id:               String,
        session_id:             Option<String>,
        conflict_type:          String,
        human_statement:        String,
        prior_memory_id:        Option<String>,
        correct_interpretation: Option<String>,
    ) -> Result<JsConflictTrace> {
        let ct = match conflict_type.as_str() {
            "misinterpretation"     => ConflictType::Misinterpretation,
            "agent_stands_firm"     => ConflictType::AgentStandsFirm,
            "factual_contradiction" => ConflictType::FactualContradiction,
            other => return Err(Error::from_reason(
                format!("unknown conflict_type: {}", other)
            )),
        };
        let core = self.inner.lock().await;
        let result = core.resolve_conflict(ConflictInput {
            agent_id, session_id, conflict_type: ct,
            human_statement, prior_memory_id, correct_interpretation,
        })
        .await
        .map_err(|e| Error::from_reason(e.to_string()))?;

        Ok(JsConflictTrace {
            agent_response:  result.agent_response,
            halt_reasoning:  result.halt_reasoning,
            resolution:      format!("{:?}", result.resolution),
            interpretation_version: result.interpretation_version,
        })
    }

    /// Get assembled working memory context for prompt injection.
    #[napi]
    pub async fn context(&self, agent_id: String) -> Result<Vec<JsWorkingMemory>> {
        let core = self.inner.lock().await;
        let layers = core.context(&agent_id)
            .await
            .map_err(|e| Error::from_reason(e.to_string()))?;
        Ok(layers.into_iter().map(JsWorkingMemory::from).collect())
    }

    /// Run an analytics query.
    /// query: "decay_tuning" | "recall_health" | "conflict_patterns" |
    ///        "memory_growth" | "reinforcement" | "session_patterns" | "summary" | "available"
    #[napi]
    pub async fn analytics(
        &self,
        agent_id:    String,
        query:       String,
        window_days: Option<i64>,
    ) -> Result<String> {
        let core = self.inner.lock().await;
        let result = core.analytics(&agent_id, &query, window_days.unwrap_or(30))
            .await
            .map_err(|e| Error::from_reason(e.to_string()))?;
        // napi cannot return `serde_json::Value` directly; hand back a JSON string.
        serde_json::to_string(&result)
            .map_err(|e| Error::from_reason(e.to_string()))
    }

    /// Clear active episode when a session ends.
    #[napi]
    pub async fn end_session(&self, agent_id: String) -> Result<()> {
        let core = self.inner.lock().await;
        core.end_session(&agent_id)
            .await
            .map_err(|e| Error::from_reason(e.to_string()))
    }
}

// ---------------------------------------------------------------------------
// JS-facing input/output types
// ---------------------------------------------------------------------------

#[napi(object)]
pub struct JsMemoryInput {
    pub agent_id:         String,
    pub content:          String,
    pub category:         String,
    pub session_id:       Option<String>,
    pub importance:       Option<f64>,
    pub confidence:       Option<f64>,
    pub keywords:         Option<Vec<String>>,
    pub tags:             Option<Vec<String>>,
    pub epistemic_status: Option<String>,
}

impl From<JsMemoryInput> for MemoryInput {
    fn from(js: JsMemoryInput) -> Self {
        Self {
            agent_id:         js.agent_id,
            content:          js.content,
            category:         parse_category(&js.category),
            session_id:       js.session_id,
            importance:       js.importance,
            confidence:       js.confidence,
            keywords:         js.keywords,
            tags:             js.tags,
            epistemic_status: js.epistemic_status.as_deref().map(parse_epistemic),
            summary:          None,
            scope:            None,
            valid_time_start: None,
            valid_time_end:   None,
            source_kind:      None,
            source_ref:       None,
            source_trust:     None,
            derived_from:     None,
            embedding:        None,
            decay_lambda:     None,
        }
    }
}

#[napi(object)]
pub struct JsMemory {
    pub id:               Option<String>,
    pub category:         String,
    pub content:          String,
    pub agent_id:         String,
    pub confidence:       f64,
    pub importance:       f64,
    pub epistemic_status: String,
    pub superseded:       bool,
    pub known_time:       Option<String>,
}

impl From<agent_memory::Memory> for JsMemory {
    fn from(m: agent_memory::Memory) -> Self {
        Self {
            id:               m.id.map(|id| id.key_str()),
            category:         format!("{:?}", m.category).to_lowercase(),
            content:          m.content,
            agent_id:         m.agent_id,
            confidence:       m.confidence,
            importance:       m.importance,
            epistemic_status: format!("{:?}", m.epistemic_status).to_lowercase(),
            superseded:       m.superseded,
            known_time:       m.known_time.map(|t| t.to_rfc3339()),
        }
    }
}

#[napi(object)]
pub struct JsRecallQuery {
    pub agent_id:    String,
    pub query_text:  String,
    pub top_k:       Option<i32>,
    pub categories:  Option<Vec<String>>,
    pub session_id:  Option<String>,
    pub min_confidence: Option<f64>,
}

impl From<JsRecallQuery> for RecallQuery {
    fn from(js: JsRecallQuery) -> Self {
        Self {
            agent_id:        js.agent_id,
            query_text:      js.query_text,
            top_k:           js.top_k.unwrap_or(10) as usize,
            categories:      js.categories.map(|cs| cs.iter().map(|c| parse_category(c)).collect()),
            session_id:      js.session_id,
            min_confidence:  js.min_confidence.unwrap_or(0.0),
            tier:            RetrievalTier::Hybrid,
            ..Default::default()
        }
    }
}

#[napi(object)]
pub struct JsRecallResult {
    pub memories:   Vec<JsMemory>,
    pub tier_used:  i32,
    pub candidates: i32,
}

impl From<agent_memory::RecallResult> for JsRecallResult {
    fn from(r: agent_memory::RecallResult) -> Self {
        Self {
            memories:   r.memories.into_iter().map(JsMemory::from).collect(),
            tier_used:  r.tier_used as i32,
            candidates: r.candidates as i32,
        }
    }
}

#[napi(object)]
pub struct JsRecallOutcome {
    /// "found" | "gap"
    pub outcome:          String,
    pub memories:         Option<Vec<JsMemory>>,
    pub gap_probe_id:     Option<String>,
    pub suggested_prompt: Option<String>,
    pub tiers_tried:      Option<Vec<i32>>,
}

impl From<agent_memory::RecallOutcome> for JsRecallOutcome {
    fn from(o: agent_memory::RecallOutcome) -> Self {
        match o {
            agent_memory::RecallOutcome::Found(r) => Self {
                outcome:          "found".to_string(),
                memories:         Some(r.memories.into_iter().map(JsMemory::from).collect()),
                gap_probe_id:     None,
                suggested_prompt: None,
                tiers_tried:      None,
            },
            agent_memory::RecallOutcome::Gap(g) => Self {
                outcome:          "gap".to_string(),
                memories:         None,
                gap_probe_id:     g.id.map(|id| id.key_str()),
                suggested_prompt: Some(g.suggested_prompt),
                tiers_tried:      Some(g.tiers_tried),
            },
        }
    }
}

#[napi(object)]
pub struct JsUpdateResult {
    pub superseded: JsMemory,
    pub new:        JsMemory,
}

#[napi(object)]
pub struct JsConflictTrace {
    pub agent_response:          String,
    pub halt_reasoning:          bool,
    pub resolution:              String,
    pub interpretation_version:  Option<i64>,
}

#[napi(object)]
pub struct JsWorkingMemory {
    pub layer:       String,
    pub content:     String,
    pub token_count: Option<i64>,
}

impl From<agent_memory::WorkingMemory> for JsWorkingMemory {
    fn from(wm: agent_memory::WorkingMemory) -> Self {
        Self {
            layer:       format!("{:?}", wm.layer).to_lowercase(),
            content:     wm.content,
            token_count: wm.token_count,
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn parse_category(s: &str) -> MemoryCategory {
    match s {
        "episodic"    => MemoryCategory::Episodic,
        "identity"    => MemoryCategory::Identity,
        "knowledge"   => MemoryCategory::Knowledge,
        "context"     => MemoryCategory::Context,
        "instruction" => MemoryCategory::Instruction,
        "uncertainty" => MemoryCategory::Uncertainty,
        _             => MemoryCategory::Knowledge,
    }
}

fn parse_epistemic(s: &str) -> EpistemicStatus {
    match s {
        "fact"       => EpistemicStatus::Fact,
        "belief"     => EpistemicStatus::Belief,
        "assumption" => EpistemicStatus::Assumption,
        "hearsay"    => EpistemicStatus::Hearsay,
        "inferred"   => EpistemicStatus::Inferred,
        _            => EpistemicStatus::Belief,
    }
}
