/// Agent-Memory — open memory layer for AI agents.
///
/// Embedded SurrealDB, Ebbinghaus decay, episodic replay,
/// conflict resolution, gap protocol. Single binary or library.
///
/// # Quick start
///
/// ```rust,no_run
/// use agent_memory::{AgentMemory, MemoryInput, MemoryCategory, RecallQuery};
///
/// #[tokio::main]
/// async fn main() -> anyhow::Result<()> {
///     let memory = AgentMemory::open("./data").await?;
///
///     memory.remember(MemoryInput {
///         agent_id:  "my-agent".to_string(),
///         content:   "User prefers concise responses".to_string(),
///         category:  MemoryCategory::Identity,
///         importance: Some(0.9),
///         ..Default::default()
///     }).await?;
///
///     let result = memory.recall(RecallQuery {
///         agent_id:  "my-agent".to_string(),
///         query_text: "user preferences".to_string(),
///         ..Default::default()
///     }).await?;
///
///     println!("{} memories", result.memories.len());
///     Ok(())
/// }
/// ```

// Internal modules — not part of the public API
mod analytics;
mod config;
mod memory;
mod server;
mod services;

// Re-export the public surface
pub use config::Config;
pub use memory::types::{
    DecisionStatus,
    EdgeKind,
    EpistemicStatus,
    EvolutionStatus,
    Memory,
    MemoryCategory,
    MemoryInput,
    MemoryScope,
    RecallQuery,
    RecallResult,
    RecordIdExt,
    RetrievalTier,
    SourceKind,
    SupersedeInput,
    WorkingMemory,
    WorkingMemoryLayer,
};
pub use memory::gap::{GapProbeRecord, RecallOutcome, ReplayedEpisode};
pub use memory::conflict::{ConflictInput, ConflictTrace, ConflictType, Resolution};
pub use analytics::engine::{AnalyticsResult, Finding, Recommendation, Severity};

use anyhow::Result;
use memory::{service::MemoryService, store::Store};

// ---------------------------------------------------------------------------
// AgentMemory — the single public entry point
// ---------------------------------------------------------------------------

/// The Agent-Memory runtime.
///
/// Boots embedded SurrealDB, applies migrations, starts background workers.
/// All memory operations go through this struct.
///
/// Create one per agent process. It is `Clone` — share freely across tasks.
#[derive(Clone)]
pub struct AgentMemory {
    service: MemoryService,
}

impl AgentMemory {
    /// Open (or create) a persistent memory store at `data_dir`.
    pub async fn open(data_dir: impl AsRef<std::path::Path>) -> Result<Self> {
        let cfg = Config::load(&data_dir.as_ref().join("config.toml"))?;
        let store = Store::open(data_dir.as_ref().to_path_buf()).await?;
        Ok(Self { service: MemoryService::new(store, cfg) })
    }

    /// Open an ephemeral in-memory store. Data lost on drop. Useful for tests.
    pub async fn open_mem() -> Result<Self> {
        let store = Store::open_mem().await?;
        Ok(Self { service: MemoryService::new(store, Config::default()) })
    }

    /// Open with explicit config.
    pub async fn open_with_config(
        data_dir: impl AsRef<std::path::Path>,
        config:   Config,
    ) -> Result<Self> {
        let store = Store::open(data_dir.as_ref().to_path_buf()).await?;
        Ok(Self { service: MemoryService::new(store, config) })
    }

    // -----------------------------------------------------------------------
    // Core memory operations
    // -----------------------------------------------------------------------

    /// Store a new memory.
    pub async fn remember(&self, input: MemoryInput) -> Result<Memory> {
        self.service.remember(input).await
    }

    /// Retrieve memories using hybrid search (BM25 + vector + RRF).
    pub async fn recall(&self, query: RecallQuery) -> Result<RecallResult> {
        self.service.recall(query).await
    }

    /// Recall with full escalation — tries all tiers before giving up.
    /// Returns `Found`, `Gap` (with suggested prompt), or after replay `EpisodeReplayed`.
    pub async fn recall_or_gap(
        &self,
        query:            RecallQuery,
        human_insistence: Option<String>,
    ) -> Result<RecallOutcome> {
        self.service.recall_or_gap(query, human_insistence).await
    }

    /// Supersede a memory — old record preserved, new record created.
    /// Spectron model: history is never lost.
    pub async fn update(&self, input: SupersedeInput) -> Result<(Memory, Memory)> {
        self.service.update(input).await
    }

    /// Soft-forget a memory. History remains queryable.
    pub async fn forget(&self, memory_id: &str) -> Result<()> {
        self.service.forget(memory_id).await
    }

    /// Hard purge — GDPR / legal only. Removes the record entirely.
    pub async fn purge(&self, memory_id: &str) -> Result<()> {
        self.service.purge(memory_id).await
    }

    // -----------------------------------------------------------------------
    // Episode replay
    // -----------------------------------------------------------------------

    /// Replay a complete past session into active context.
    /// Human provides a time window anchor.
    pub async fn replay_session(
        &self,
        agent_id:     &str,
        session_id:   &str,
        gap_probe_id: Option<surrealdb::types::RecordId>,
    ) -> Result<ReplayedEpisode> {
        self.service.replay_session(agent_id, session_id, gap_probe_id).await
    }

    /// Replay sessions matching a time window.
    pub async fn replay_by_window(
        &self,
        agent_id:     &str,
        window_start: chrono::DateTime<chrono::Utc>,
        window_end:   chrono::DateTime<chrono::Utc>,
        topic_hint:   Option<String>,
        gap_probe_id: Option<surrealdb::types::RecordId>,
    ) -> Result<Option<ReplayedEpisode>> {
        self.service.replay_by_window(
            agent_id, window_start, window_end, topic_hint, gap_probe_id
        ).await
    }

    // -----------------------------------------------------------------------
    // Conflict resolution
    // -----------------------------------------------------------------------

    /// Resolve a conflict between what the agent has and what the human says.
    ///
    /// - `Misinterpretation` → human corrects the agent's interpretation
    /// - `AgentStandsFirm`   → agent shows its log, stands firm
    /// - `FactualContradiction` → agent halts reasoning on that thread
    pub async fn resolve_conflict(&self, input: ConflictInput) -> Result<ConflictTrace> {
        self.service.resolve_conflict(input).await
    }

    /// Return recent conflict traces for an agent.
    pub async fn conflict_history(
        &self,
        agent_id: &str,
        limit:    usize,
    ) -> Result<Vec<memory::conflict::ConflictTraceRow>> {
        self.service.conflict_history(agent_id, limit).await
    }

    // -----------------------------------------------------------------------
    // Reinforcement
    // -----------------------------------------------------------------------

    /// Reinforce a set of memories — resets their decay.
    pub async fn reinforce(&self, memory_ids: &[String]) -> Result<()> {
        self.service.reinforce(memory_ids).await
    }

    // -----------------------------------------------------------------------
    // Context
    // -----------------------------------------------------------------------

    /// Assembled working memory layers for prompt injection.
    pub async fn context(&self, agent_id: &str) -> Result<Vec<WorkingMemory>> {
        self.service.full_context(agent_id).await
    }

    // -----------------------------------------------------------------------
    // Analytics
    // -----------------------------------------------------------------------

    /// Run a telemetry/analytics query.
    ///
    /// Built-in queries: `decay_tuning`, `recall_health`, `conflict_patterns`,
    /// `memory_growth`, `reinforcement`, `session_patterns`, `summary`, `available`.
    pub async fn analytics(
        &self,
        agent_id:    &str,
        query:       &str,
        window_days: i64,
    ) -> Result<AnalyticsResult> {
        use std::sync::Arc;
        let engine = analytics::engine::AnalyticsEngine::new(
            Arc::new(self.service.store.clone()),
            Arc::new(self.service.config.clone()),
        );
        engine.run(agent_id, query, window_days).await
    }

    // -----------------------------------------------------------------------
    // Session lifecycle
    // -----------------------------------------------------------------------

    /// Clear active episode when a session ends.
    pub async fn end_session(&self, agent_id: &str) -> Result<()> {
        self.service.end_session(agent_id).await
    }

    /// Store something the human re-stated after a gap probe.
    pub async fn store_restated_belief(
        &self,
        agent_id:     &str,
        session_id:   Option<String>,
        content:      String,
        category:     MemoryCategory,
        gap_probe_id: Option<String>,
    ) -> Result<Memory> {
        self.service.store_restated_belief(
            agent_id, session_id, content, category, gap_probe_id
        ).await
    }
}
