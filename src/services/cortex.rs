use std::time::Duration;

use anyhow::Result;
use chrono::{Timelike, Utc};
use tracing::{debug, error, info};

use crate::memory::{
    service::MemoryService,
    types::{MemoryCategory, RecallQuery, RetrievalTier, WorkingMemory, WorkingMemoryLayer},
};

// ---------------------------------------------------------------------------
// CortexSynthesiser
//
// Maintains the five working_memory layers (Spacebot Cortex pattern).
// Never called per LLM call — runs on schedule or on graph-change events.
//
// synthesise_fn: async fn(layer, memories_or_text, agent_id) -> String
//   In production this is an LLM call with a cheap/fast model.
//   Injected by the caller. The binary does not own the LLM call.
//
// Schedule:
//   intraday_synthesis → every `interval` (default 1h)
//   daily_rollup       → once per day at midnight
//   knowledge_brief    → on demand / after evolution completes
// ---------------------------------------------------------------------------

pub struct CortexSynthesiser {
    service:      MemoryService,
    interval:     Duration,
    agent_ids:    Vec<String>,
    synthesise_fn: SynthesiseFn,
}

/// A synthesis function: given a layer label and source text, return compressed content.
/// Caller injects this — typically an LLM call.
pub type SynthesiseFn = std::sync::Arc<
    dyn Fn(WorkingMemoryLayer, String, String) -> std::pin::Pin<
        Box<dyn std::future::Future<Output = Result<String>> + Send>
    > + Send + Sync
>;

impl CortexSynthesiser {
    pub fn new(
        service:       MemoryService,
        interval:      Duration,
        agent_ids:     Vec<String>,
        synthesise_fn: SynthesiseFn,
    ) -> Self {
        Self { service, interval, agent_ids, synthesise_fn }
    }

    /// Run the cortex loop forever.
    /// Spawn as: `tokio::spawn(cortex.run())`.
    pub async fn run(self) {
        info!(
            "CortexSynthesiser started — interval={}s",
            self.interval.as_secs()
        );

        let mut last_rollup_day: Option<u32> = None;

        loop {
            let now = Utc::now();

            for agent_id in &self.agent_ids {
                // Intraday synthesis — every interval
                if let Err(e) = self.refresh_intraday(agent_id).await {
                    error!("cortex intraday error for {}: {}", agent_id, e);
                }

                // Daily rollup — once per day at midnight (hour 0)
                let today = now.day();
                if now.hour() == 0 && last_rollup_day != Some(today) {
                    if let Err(e) = self.refresh_daily_rollup(agent_id, now).await {
                        error!("cortex daily rollup error for {}: {}", agent_id, e);
                    }
                    last_rollup_day = Some(today);
                }
            }

            tokio::time::sleep(self.interval).await;
        }
    }

    /// Compress today's episodic + knowledge memories into a narrative.
    pub async fn refresh_intraday(&self, agent_id: &str) -> Result<WorkingMemory> {
        let today_start = Utc::now()
            .date_naive()
            .and_hms_opt(0, 0, 0)
            .map(|dt| dt.and_utc())
            .unwrap_or_else(Utc::now);

        let result = self.service.recall(RecallQuery {
            agent_id:    agent_id.to_string(),
            query_text:  String::new(),
            categories:  Some(vec![MemoryCategory::Episodic, MemoryCategory::Knowledge]),
            top_k:       50,
            tier:        RetrievalTier::DirectLookup,
            valid_at:    Some(Utc::now()),
            ..Default::default()
        }).await?;

        let recent: Vec<_> = result.memories.iter()
            .filter(|m| m.known_time.map(|t| t >= today_start).unwrap_or(false))
            .cloned()
            .collect();

        let source_text = recent.iter()
            .map(|m| format!("[{}] {}", m.category_str(), m.content))
            .collect::<Vec<_>>()
            .join("\n");

        let content = (self.synthesise_fn)(
            WorkingMemoryLayer::IntradaySynthesis,
            source_text,
            agent_id.to_string(),
        ).await?;

        let token_count = content.split_whitespace().count() as i64;
        let source_ids: Vec<_> = recent.iter()
            .filter_map(|m| m.id.clone())
            .collect();

        let wm = WorkingMemory {
            id:              None,
            agent_id:        agent_id.to_string(),
            layer:           WorkingMemoryLayer::IntradaySynthesis,
            content,
            source_memories: Some(source_ids),
            valid_date:      Some(Utc::now()),
            token_count:     Some(token_count),
            created_at:      None,
            updated_at:      None,
        };

        let result = self.service.upsert_working_memory(wm).await?;
        debug!("cortex: refreshed intraday_synthesis for agent {}", agent_id);
        Ok(result)
    }

    /// Midnight job: compress intraday into daily summary.
    pub async fn refresh_daily_rollup(
        &self,
        agent_id: &str,
        date: chrono::DateTime<Utc>,
    ) -> Result<WorkingMemory> {
        let existing = self.service.store
            .get_working_memory(agent_id, Some(vec![WorkingMemoryLayer::IntradaySynthesis]))
            .await?;

        let source_text = existing.first()
            .map(|wm| wm.content.clone())
            .unwrap_or_default();

        let content = (self.synthesise_fn)(
            WorkingMemoryLayer::DailyRollup,
            source_text,
            agent_id.to_string(),
        ).await?;

        let token_count = content.split_whitespace().count() as i64;

        let wm = WorkingMemory {
            id:              None,
            agent_id:        agent_id.to_string(),
            layer:           WorkingMemoryLayer::DailyRollup,
            content,
            source_memories: None,
            valid_date:      Some(date),
            token_count:     Some(token_count),
            created_at:      None,
            updated_at:      None,
        };

        let result = self.service.upsert_working_memory(wm).await?;
        info!("cortex: daily rollup for agent {} on {}", agent_id, date.date_naive());
        Ok(result)
    }

    /// Change-driven: regenerate when memory graph changes.
    pub async fn refresh_knowledge_brief(&self, agent_id: &str) -> Result<WorkingMemory> {
        let result = self.service.recall(RecallQuery {
            agent_id:   agent_id.to_string(),
            query_text: String::new(),
            categories: Some(vec![MemoryCategory::Identity, MemoryCategory::Knowledge]),
            top_k:      30,
            tier:       RetrievalTier::DirectLookup,
            ..Default::default()
        }).await?;

        let source_text = result.memories.iter()
            .map(|m| format!("[{}] {}", m.category_str(), m.content))
            .collect::<Vec<_>>()
            .join("\n");

        let content = (self.synthesise_fn)(
            WorkingMemoryLayer::KnowledgeBrief,
            source_text,
            agent_id.to_string(),
        ).await?;

        let token_count = content.split_whitespace().count() as i64;
        let source_ids: Vec<_> = result.memories.iter()
            .filter_map(|m| m.id.clone())
            .collect();

        let wm = WorkingMemory {
            id:              None,
            agent_id:        agent_id.to_string(),
            layer:           WorkingMemoryLayer::KnowledgeBrief,
            content,
            source_memories: Some(source_ids),
            valid_date:      Some(Utc::now()),
            token_count:     Some(token_count),
            created_at:      None,
            updated_at:      None,
        };

        let result = self.service.upsert_working_memory(wm).await?;
        debug!("cortex: refreshed knowledge_brief for agent {}", agent_id);
        Ok(result)
    }
}

// Helper on Memory for display
impl crate::memory::types::Memory {
    pub fn category_str(&self) -> &'static str {
        match self.category {
            crate::memory::types::MemoryCategory::Episodic     => "episodic",
            crate::memory::types::MemoryCategory::Identity     => "identity",
            crate::memory::types::MemoryCategory::Knowledge    => "knowledge",
            crate::memory::types::MemoryCategory::Context      => "context",
            crate::memory::types::MemoryCategory::Instruction  => "instruction",
            crate::memory::types::MemoryCategory::Uncertainty  => "uncertainty",
        }
    }
}

// Needed for date arithmetic
use chrono::Datelike;
