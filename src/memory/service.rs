use anyhow::Result;
use chrono::Utc;
use tracing::{debug, warn};

use crate::memory::{
    store::{reciprocal_rank_fusion, Store},
    types::*,
};

const CONFIDENCE_FLOOR: f64 = 0.4;

// ---------------------------------------------------------------------------
// MemoryService — the public API used by agent runtime and MCP server
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct MemoryService {
    pub store:  Store,
    pub config: crate::config::Config,
}

impl MemoryService {
    pub fn new(store: Store, config: crate::config::Config) -> Self {
        Self { store, config }
    }

    // -----------------------------------------------------------------------
    // Write operations
    // -----------------------------------------------------------------------

    pub async fn remember(&self, input: MemoryInput) -> Result<Memory> {
        // Compute config-driven decay lambda before storing
        let lambda = self.config.lambda_for_category(
            &input.category,
            &input.epistemic_status.as_ref().unwrap_or(
                &crate::memory::types::EpistemicStatus::Belief
            ),
        );
        let input = crate::memory::types::MemoryInput {
            decay_lambda: Some(lambda),
            ..input
        };
        let mem = self.store.create_memory(input).await?;
        debug!("created memory {:?} ({})", mem.id, serde_json::to_value(&mem.category).unwrap_or_default());
        Ok(mem)
    }

    /// Spectron: supersede-not-overwrite.
    pub async fn update(&self, input: SupersedeInput) -> Result<(Memory, Memory)> {
        let (old, new) = self.store.supersede_memory(input).await?;
        debug!("superseded {:?} → {:?}", old.id, new.id);
        Ok((old, new))
    }

    /// Soft forget — valid_time_end = now, superseded = true.
    /// History remains queryable.
    pub async fn forget(&self, memory_id: &str) -> Result<()> {
        self.store.forget(memory_id).await?;
        debug!("forgot (soft) {}", memory_id);
        Ok(())
    }

    /// Hard purge — removes all derived rows. Use only for GDPR/legal.
    pub async fn purge(&self, memory_id: &str) -> Result<()> {
        self.store.purge(memory_id).await?;
        warn!("PURGED memory {}", memory_id);
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Retrieval — four-tier ladder
    // -----------------------------------------------------------------------

    pub async fn recall(&self, q: RecallQuery) -> Result<RecallResult> {
        match q.tier {
            RetrievalTier::DirectLookup => self.recall_direct(q).await,
            RetrievalTier::Hybrid | RetrievalTier::FullContext => self.recall_hybrid(q).await,
            RetrievalTier::ResponseReuse => self.recall_hybrid(q).await, // fallback
        }
    }

    async fn recall_direct(&self, q: RecallQuery) -> Result<RecallResult> {
        let memories = self.store.direct_lookup(&q).await?;
        let ids: Vec<String> = memories.iter()
            .filter_map(|m| m.id.as_ref().map(|id| id.key_str()))
            .collect();

        let trace = self.store.write_trace(&q, &ids, RetrievalTier::DirectLookup).await.ok();

        let result = RecallResult {
            candidates: memories.len(),
            memories,
            trace_id: trace.and_then(|t| t.id),
            tier_used: RetrievalTier::DirectLookup,
        };
        // Reinforce retrieved memories — resets decay
        for m in &result.memories {
            if let Some(ref id) = m.id {
                let _ = self.store.reinforce_memory(&id.key_str()).await;
            }
        }
        Ok(result)
    }

    async fn recall_hybrid(&self, q: RecallQuery) -> Result<RecallResult> {
        // Run BM25 and vector searches concurrently
        let (bm25_res, vec_res) = tokio::join!(
            self.store.bm25_search(&q),
            self.store.vector_search(&q),
        );

        let bm25 = bm25_res.unwrap_or_default();
        let vec  = vec_res.unwrap_or_default();

        let total_candidates = bm25.len() + vec.len();

        // Convert to (id, score) pairs for RRF
        let bm25_pairs: Vec<(String, f32)> = bm25.iter()
            .filter_map(|(m, s)| m.id.as_ref().map(|id| (id.key_str(), *s)))
            .collect();
        let vec_pairs: Vec<(String, f32)> = vec.iter()
            .filter_map(|(m, s)| m.id.as_ref().map(|id| (id.key_str(), *s)))
            .collect();

        // RRF merge
        let merged_ids = reciprocal_rank_fusion(&bm25_pairs, &vec_pairs, 60, q.top_k);

        // Fetch full records for merged IDs
        let memories = self.store.fetch_by_ids(&merged_ids).await?;

        let ids: Vec<String> = memories.iter()
            .filter_map(|m| m.id.as_ref().map(|id| id.key_str()))
            .collect();

        let trace = self.store.write_trace(&q, &ids, q.tier).await.ok();

        let result = RecallResult {
            memories,
            trace_id: trace.and_then(|t| t.id),
            tier_used: q.tier,
            candidates: total_candidates,
        };
        // Reinforce retrieved memories — resets decay
        for m in &result.memories {
            if let Some(ref id) = m.id {
                let _ = self.store.reinforce_memory(&id.key_str()).await;
            }
        }
        Ok(result)
    }

    /// Feedback on a retrieval trace — boosts or demotes future rankings.
    pub async fn feedback(
        &self,
        trace_id: &str,
        useful: Option<bool>,
        correction: Option<bool>,
    ) -> Result<()> {
        self.store.feedback_trace(trace_id, useful, correction).await
    }

    // -----------------------------------------------------------------------
    // Graph
    // -----------------------------------------------------------------------

    pub async fn relate(
        &self,
        source_id: &str,
        target_id: &str,
        kind: EdgeKind,
        weight: f64,
    ) -> Result<()> {
        self.store.relate(source_id, target_id, kind, weight).await
    }

    pub async fn related(
        &self,
        memory_id: &str,
        kinds: Option<Vec<EdgeKind>>,
    ) -> Result<Vec<Memory>> {
        self.store.related_memories(memory_id, kinds).await
    }

    // -----------------------------------------------------------------------
    // Temporal
    // -----------------------------------------------------------------------

    pub async fn at(&self, agent_id: &str, point_in_time: chrono::DateTime<Utc>, categories: Option<Vec<MemoryCategory>>) -> Result<Vec<Memory>> {
        self.store.memories_valid_at(agent_id, point_in_time, categories).await
    }

    pub async fn history(&self, memory_id: &str) -> Result<Vec<Memory>> {
        self.store.supersession_lineage(memory_id).await
    }

    // -----------------------------------------------------------------------
    // Cortex — assembled working memory for prompt injection
    // -----------------------------------------------------------------------

    pub async fn context(&self, agent_id: &str) -> Result<Vec<WorkingMemory>> {
        self.store.get_working_memory(agent_id, Some(vec![
            WorkingMemoryLayer::IdentityContext,
            WorkingMemoryLayer::IntradaySynthesis,
            WorkingMemoryLayer::CrossAgentMap,
            WorkingMemoryLayer::KnowledgeBrief,
        ])).await
    }

    pub async fn upsert_working_memory(&self, wm: WorkingMemory) -> Result<WorkingMemory> {
        self.store.upsert_working_memory(&wm).await
    }

    // -----------------------------------------------------------------------
    // Decision trace
    // -----------------------------------------------------------------------

    pub async fn trace_decision(&self, dt: DecisionTrace) -> Result<DecisionTrace> {
        self.store.create_decision_trace(&dt).await
    }

    // -----------------------------------------------------------------------
    // Reconciler — Spectron calibration + contradiction detection
    // Called by EvolutionWorker after link generation
    // -----------------------------------------------------------------------

    pub async fn reconcile(
        &self,
        agent_id: &str,
        new_memory_id: &str,
        related: &[Memory],
    ) -> Result<()> {
        let new_mem = match self.store.select_memory(new_memory_id).await? {
            Some(m) => m,
            None => return Ok(()),
        };

        for related_mem in related {
            let related_id = match &related_mem.id {
                Some(id) => id.key_str(),
                None => continue,
            };

            // Spectron calibration guard:
            // Low-confidence new memory MUST NOT supersede high-confidence existing one.
            // If it would, emit an uncertainty row instead.
            if new_mem.confidence < CONFIDENCE_FLOOR
                && related_mem.confidence > new_mem.confidence
            {
                let uncertainty = MemoryInput {
                    category: MemoryCategory::Uncertainty,
                    content: format!(
                        "Conflict: memory {} (confidence {:.2}) conflicts with {} (confidence {:.2}) — below reconciler floor {:.2}",
                        new_memory_id, new_mem.confidence,
                        related_id, related_mem.confidence,
                        CONFIDENCE_FLOOR
                    ),
                    agent_id: agent_id.to_string(),
                    source_kind: Some(SourceKind::Consolidation),
                    confidence: Some(new_mem.confidence),
                    importance: Some(0.6),
                    summary: None,
                    session_id: None,
                    scope: None,
                    valid_time_start: None,
                    valid_time_end: None,
                    source_ref: None,
                    source_trust: None,
                    derived_from: Some(vec![new_memory_id.to_string(), related_id.clone()]),
                    keywords: None,
                    tags: None,
                    embedding: None,
                    epistemic_status: None,
                    decay_lambda: None,
                };
                self.store.create_memory(uncertainty).await?;
                warn!("reconciler: emitted uncertainty for {} vs {}", new_memory_id, related_id);
                continue;
            }

            // Create related_to edge between new and related
            self.store.relate(
                new_memory_id,
                &related_id,
                EdgeKind::RelatedTo,
                0.8,
            ).await?;
        }

        Ok(())
    }
}
