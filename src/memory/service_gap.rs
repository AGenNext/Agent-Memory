/// Gap protocol methods on MemoryService.
/// Imported via `use crate::memory::service_gap::*;` in service.rs

use anyhow::Result;
use chrono::{DateTime, Utc};
use tracing::{debug, info};

use crate::memory::{
    conflict::{ConflictInput, ConflictResolver, ConflictTrace},
    gap::{EpisodicReplay, EscalatingRecall, RecallOutcome, ReplayedEpisode},
    service::MemoryService,
    types::{
        MemoryCategory, MemoryInput, RecallQuery, SourceKind, WorkingMemory,
        WorkingMemoryLayer,
    },
};

impl MemoryService {
    // -----------------------------------------------------------------------
    // Escalating recall — the human-like "try everything" path
    // -----------------------------------------------------------------------

    /// Try to recall something, escalating through all tiers.
    /// Returns Found, Gap, or EpisodeReplayed.
    ///
    /// human_insistence: what the human said that triggered this search.
    /// Pass Some("I told you last week about X") to get a better gap prompt.
    pub async fn recall_or_gap(
        &self,
        q:                RecallQuery,
        human_insistence: Option<String>,
    ) -> Result<RecallOutcome> {
        EscalatingRecall::new(
            &self.store,
            &q,
            human_insistence,
            self.config.retrieval_threshold(),
            self.config.escalating_threshold(),
        )
        .run()
        .await
    }

    // -----------------------------------------------------------------------
    // Episode replay — human provides a time anchor
    // -----------------------------------------------------------------------

    /// Human says "we discussed this on Tuesday around 3pm".
    /// Caller resolves the natural language to a time window and calls this.
    /// Returns the replayed episode, which is also stored in active_episode.
    pub async fn replay_by_window(
        &self,
        agent_id:     &str,
        window_start: DateTime<Utc>,
        window_end:   DateTime<Utc>,
        topic_hint:   Option<String>,
        gap_probe_id: Option<surrealdb::RecordId>,
    ) -> Result<Option<ReplayedEpisode>> {
        let replay = EpisodicReplay::new(&self.store);
        let episode = replay.replay_by_time(
            agent_id,
            window_start,
            window_end,
            topic_hint,
            gap_probe_id,
        ).await?;

        if let Some(ref ep) = episode {
            // Load the thread text into working_memory as ActiveEpisode layer
            // so it gets injected into the agent's prompt context
            self.store.upsert_working_memory(&WorkingMemory {
                id:              None,
                agent_id:        agent_id.to_string(),
                layer:           WorkingMemoryLayer::ActiveEpisode,
                content:         ep.thread_text.clone(),
                source_memories: Some(ep.memories.iter().filter_map(|m| m.id.clone()).collect()),
                valid_date:      Some(ep.started_at),
                token_count:     Some(ep.token_count as i64),
                created_at:      None,
                updated_at:      None,
            }).await?;

            info!("episode replayed into active context: session {} ({} memories, {} tokens)",
                ep.session_id, ep.memories.len(), ep.token_count);
        }

        Ok(episode)
    }

    /// Replay a specific session by session_id directly.
    /// Used when the human says "yes, that was session X" or
    /// when we have a session_id from a gap probe.
    pub async fn replay_session(
        &self,
        agent_id:     &str,
        session_id:   &str,
        gap_probe_id: Option<surrealdb::RecordId>,
    ) -> Result<ReplayedEpisode> {
        let replay = EpisodicReplay::new(&self.store);
        let episode = replay.replay_session(agent_id, session_id, gap_probe_id).await?;

        // Load into active context
        self.store.upsert_working_memory(&WorkingMemory {
            id:              None,
            agent_id:        agent_id.to_string(),
            layer:           WorkingMemoryLayer::ActiveEpisode,
            content:         episode.thread_text.clone(),
            source_memories: Some(episode.memories.iter().filter_map(|m| m.id.clone()).collect()),
            valid_date:      Some(episode.started_at),
            token_count:     Some(episode.token_count as i64),
            created_at:      None,
            updated_at:      None,
        }).await?;

        Ok(episode)
    }

    // -----------------------------------------------------------------------
    // Reinforcement — called when a recalled memory is confirmed useful
    // -----------------------------------------------------------------------

    /// Reinforce a set of memories — reset their decay.
    /// Called when the agent gets positive feedback (useful=true on a trace).
    pub async fn reinforce(&self, memory_ids: &[String]) -> Result<()> {
        for id in memory_ids {
            self.store.reinforce_memory(id).await?;
        }
        debug!("reinforced {} memories", memory_ids.len());
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Post-gap: human re-states something the agent didn't remember
    // Store it immediately as a belief with user_turn source
    // -----------------------------------------------------------------------

    /// Human re-states something after a gap.
    /// Store it with high source_trust (direct user statement).
    /// Optionally link to the gap probe.
    pub async fn store_restated_belief(
        &self,
        agent_id:     &str,
        session_id:   Option<String>,
        content:      String,
        category:     MemoryCategory,
        gap_probe_id: Option<String>,
    ) -> Result<crate::memory::types::Memory> {
        let mem = self.store.create_memory(MemoryInput {
            agent_id:        agent_id.to_string(),
            content,
            category,
            session_id,
            source_kind:     Some(SourceKind::UserTurn),
            source_trust:    Some(0.92), // direct user statement — high trust
            confidence:      Some(0.90),
            importance:      Some(0.8),  // high importance — we had to ask for it
            epistemic_status: Some(crate::memory::types::EpistemicStatus::Belief),
            derived_from:    gap_probe_id.map(|id| vec![id]),
            summary:         None,
            scope:           None,
            valid_time_start: None,
            valid_time_end:   None,
            source_ref:      None,
            keywords:        None,
            tags:            None,
            embedding:       None,
        }).await?;

        info!("stored restated belief {:?} for agent {}", mem.id, agent_id);
        Ok(mem)
    }

    // -----------------------------------------------------------------------
    // Clear active episode when session ends
    // -----------------------------------------------------------------------

    // -----------------------------------------------------------------------
    // Conflict resolution
    // -----------------------------------------------------------------------

    pub async fn resolve_conflict(&self, input: ConflictInput) -> Result<ConflictTrace> {
        ConflictResolver::new(&self.store).resolve(input).await
    }

    pub async fn conflict_history(
        &self,
        agent_id: &str,
        limit: usize,
    ) -> Result<Vec<crate::memory::conflict::ConflictTraceRow>> {
        self.store.conflict_history(agent_id, limit).await
    }

    pub async fn end_session(&self, agent_id: &str) -> Result<()> {
        self.store.clear_active_episode(agent_id).await?;
        debug!("cleared active episode for agent {}", agent_id);
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Assembled context — now includes active_episode if present
    // -----------------------------------------------------------------------

    pub async fn full_context(&self, agent_id: &str) -> Result<Vec<WorkingMemory>> {
        self.store.get_working_memory(agent_id, Some(vec![
            WorkingMemoryLayer::IdentityContext,
            WorkingMemoryLayer::IntradaySynthesis,
            WorkingMemoryLayer::CrossAgentMap,
            WorkingMemoryLayer::KnowledgeBrief,
            WorkingMemoryLayer::ActiveEpisode, // injected when a session is replayed
        ])).await
    }
}
