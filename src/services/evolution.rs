use std::time::Duration;

use anyhow::Result;
use chrono::Utc;
use tracing::{debug, error, info};

use crate::memory::{
    service::MemoryService,
    types::{EdgeKind, EvolutionStatus, MemoryInput, RecallQuery, RetrievalTier},
};

// ---------------------------------------------------------------------------
// EvolutionWorker
//
// Drains the evolution_queue on a configurable interval.
// For each job:
//   1. Find top-k related memories via hybrid search
//   2. Run reconciler (link generation + contradiction detection)
//   3. Optionally call evolve_fn to update context/keywords/tags
//      on related memories (A-Mem evolution)
//
// evolve_fn is injected — caller provides it. Can be an LLM call or
// rule-based. Worker does not own the LLM call.
// ---------------------------------------------------------------------------

pub struct EvolutionWorker {
    service:   MemoryService,
    interval:  Duration,
    batch:     usize,
    agent_ids: Vec<String>,
}

impl EvolutionWorker {
    pub fn new(
        service:   MemoryService,
        interval:  Duration,
        batch:     usize,
        agent_ids: Vec<String>,
    ) -> Self {
        Self { service, interval, batch, agent_ids }
    }

    /// Run the worker loop forever.
    /// Spawn this as a tokio task: `tokio::spawn(worker.run())`.
    pub async fn run(self) {
        info!(
            "EvolutionWorker started — interval={}s batch={}",
            self.interval.as_secs(),
            self.batch
        );

        loop {
            for agent_id in &self.agent_ids {
                if let Err(e) = self.process_batch(agent_id).await {
                    error!("EvolutionWorker error for agent {}: {}", agent_id, e);
                }
            }
            tokio::time::sleep(self.interval).await;
        }
    }

    async fn process_batch(&self, agent_id: &str) -> Result<usize> {
        let jobs = self.service.store
            .claim_evolution_jobs(agent_id, self.batch)
            .await?;

        if jobs.is_empty() {
            return Ok(0);
        }

        let mut processed = 0;

        for job in &jobs {
            let job_id = match &job.id {
                Some(id) => id.clone(),
                None => continue,
            };

            let new_mem_key = job.new_memory_id.key().to_string();

            let result: Result<()> = async {
                // Fetch the new memory
                let new_mem = match self.service.store.select_memory(&new_mem_key).await? {
                    Some(m) => m,
                    None => {
                        debug!("evolution job {}: memory not found, skipping", new_mem_key);
                        self.service.store.skip_evolution_job(&job_id).await?;
                        return Ok(());
                    }
                };

                // Find top-5 related memories via hybrid search
                let q = RecallQuery {
                    agent_id:    agent_id.to_string(),
                    query_text:  new_mem.content.clone(),
                    query_embedding: new_mem.embedding.clone(),
                    top_k:       5,
                    tier:        RetrievalTier::Hybrid,
                    min_confidence: 0.0,
                    include_superseded: false,
                    ..Default::default()
                };

                let result = self.service.recall(q).await?;
                let related: Vec<_> = result.memories.iter()
                    .filter(|m| {
                        m.id.as_ref().map(|id| id.key().to_string())
                            != Some(new_mem_key.clone())
                    })
                    .cloned()
                    .collect();

                // Reconciler: link generation + contradiction detection
                self.service.reconcile(agent_id, &new_mem_key, &related).await?;

                // A-Mem evolution: update evolved_at on related memories
                // to signal they were touched by this evolution pass.
                // Full context/keyword/tag evolution requires an LLM call —
                // inject via evolve_fn in extended builds.
                for related_mem in &related {
                    if let Some(rid) = &related_mem.id {
                        let rid_str = rid.key().to_string();
                        self.service.store.query_raw(&format!(
                            "UPDATE memory:{} SET evolved_at = time::now();",
                            rid_str
                        )).await?;
                    }
                }

                self.service.store.complete_evolution_job(&job_id).await?;
                Ok(())
            }.await;

            match result {
                Ok(()) => processed += 1,
                Err(e) => {
                    error!("evolution job {:?} failed: {}", job_id, e);
                    let _ = self.service.store.skip_evolution_job(&job_id).await;
                }
            }
        }

        if processed > 0 {
            debug!("EvolutionWorker: processed {} jobs for agent {}", processed, agent_id);
        }

        Ok(processed)
    }
}
