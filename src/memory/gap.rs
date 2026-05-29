use anyhow::Result;
use chrono::{DateTime, Duration, Utc};
use surrealdb::RecordId;
use tracing::{debug, info};

use crate::memory::{
    decay::{effective_confidence, ESCALATING_THRESHOLD, RETRIEVAL_THRESHOLD},
    store::Store,
    types::*,
};

// ---------------------------------------------------------------------------
// GapResult — what the service returns when recall finds nothing
//
// The agent runtime reads this and decides what to say.
// It is never an empty Vec<Memory> — it is always honest metadata.
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub enum RecallOutcome {
    /// Found memories. Normal path.
    Found(RecallResult),

    /// Found nothing after exhausting all tiers.
    /// The agent should acknowledge the gap and ask for a time anchor.
    Gap(GapProbeRecord),

    /// Human provided a time anchor. A complete past session is now
    /// loaded into active memory. The agent can see the full episode.
    EpisodeReplayed(ReplayedEpisode),
}

#[derive(Debug, Clone)]
pub struct GapProbeRecord {
    pub id:                  Option<RecordId>,
    pub agent_id:            String,
    pub session_id:          Option<String>,
    pub query_text:          String,
    pub human_insistence:    Option<String>,
    pub tiers_tried:         Vec<i32>,
    pub searched_superseded: bool,
    pub searched_temporal:   bool,
    pub searched_wider_scope: bool,
    /// Suggested question for the agent to ask the human
    pub suggested_prompt:    String,
}

#[derive(Debug, Clone)]
pub struct ReplayedEpisode {
    pub session_id:   String,
    pub started_at:   DateTime<Utc>,
    pub ended_at:     DateTime<Utc>,
    pub memories:     Vec<Memory>,
    /// Reconstructed conversation thread — ready for prompt injection
    pub thread_text:  String,
    pub token_count:  usize,
    pub gap_probe_id: Option<RecordId>,
}

// ---------------------------------------------------------------------------
// Escalating recall
//
// Tier 1: direct lookup (fast, no embedding)
// Tier 2: hybrid BM25 + vector (normal path)
// Tier 3: include superseded memories (maybe it was overwritten)
// Tier 4: temporal expansion — search past time windows
// Tier 5: scope relaxation — session → agent → team
//
// If all fail → write GapProbeRecord, return Gap(...)
// ---------------------------------------------------------------------------

pub struct EscalatingRecall<'a> {
    store:             &'a Store,
    q:                 &'a RecallQuery,
    human_insistence:  Option<String>,
}

impl<'a> EscalatingRecall<'a> {
    pub fn new(
        store:            &'a Store,
        q:                &'a RecallQuery,
        human_insistence: Option<String>,
    ) -> Self {
        Self { store, q, human_insistence }
    }

    pub async fn run(self) -> Result<RecallOutcome> {
        let now = Utc::now();

        // ----------------------------------------------------------------
        // Tier 1: direct lookup — sub-ms, no embedding
        // ----------------------------------------------------------------
        debug!("escalating recall tier 1: direct lookup");
        let direct = self.store.direct_lookup(self.q).await?;
        let direct = apply_decay_filter(direct, now, RETRIEVAL_THRESHOLD);
        if !direct.is_empty() {
            let ids = id_strings(&direct);
            let trace = self.store.write_trace(self.q, &ids, RetrievalTier::DirectLookup).await.ok();
            return Ok(RecallOutcome::Found(RecallResult {
                memories:   direct,
                trace_id:   trace.and_then(|t| t.id),
                tier_used:  RetrievalTier::DirectLookup,
                candidates: ids.len(),
            }));
        }

        // ----------------------------------------------------------------
        // Tier 2: hybrid BM25 + vector + RRF
        // ----------------------------------------------------------------
        debug!("escalating recall tier 2: hybrid");
        let (bm25_res, vec_res) = tokio::join!(
            self.store.bm25_search(self.q),
            self.store.vector_search(self.q),
        );
        let bm25 = bm25_res.unwrap_or_default();
        let vec  = vec_res.unwrap_or_default();

        let bm25_pairs: Vec<(String, f32)> = bm25.iter()
            .filter_map(|(m, s)| m.id.as_ref().map(|id| (id.key().to_string(), *s)))
            .collect();
        let vec_pairs: Vec<(String, f32)> = vec.iter()
            .filter_map(|(m, s)| m.id.as_ref().map(|id| (id.key().to_string(), *s)))
            .collect();

        let merged = crate::memory::store::reciprocal_rank_fusion(
            &bm25_pairs, &vec_pairs, 60, self.q.top_k
        );

        if !merged.is_empty() {
            let mut memories = self.store.fetch_by_ids(&merged).await?;
            memories = apply_decay_filter(memories, now, RETRIEVAL_THRESHOLD);
            if !memories.is_empty() {
                let ids = id_strings(&memories);
                let trace = self.store.write_trace(self.q, &ids, RetrievalTier::Hybrid).await.ok();
                return Ok(RecallOutcome::Found(RecallResult {
                    memories,
                    trace_id:  trace.and_then(|t| t.id),
                    tier_used: RetrievalTier::Hybrid,
                    candidates: bm25_pairs.len() + vec_pairs.len(),
                }));
            }
        }

        // ----------------------------------------------------------------
        // Tier 3: include superseded — maybe it was overwritten
        // ----------------------------------------------------------------
        debug!("escalating recall tier 3: including superseded");
        let mut q_superseded = self.q.clone();
        q_superseded.include_superseded = true;
        q_superseded.min_confidence = 0.0; // no floor — decayed memories included

        let (bm25_s, vec_s) = tokio::join!(
            self.store.bm25_search(&q_superseded),
            self.store.vector_search(&q_superseded),
        );
        let bm25_s = bm25_s.unwrap_or_default();
        let vec_s  = vec_s.unwrap_or_default();

        let bp: Vec<(String, f32)> = bm25_s.iter()
            .filter_map(|(m, s)| m.id.as_ref().map(|id| (id.key().to_string(), *s)))
            .collect();
        let vp: Vec<(String, f32)> = vec_s.iter()
            .filter_map(|(m, s)| m.id.as_ref().map(|id| (id.key().to_string(), *s)))
            .collect();

        let merged_s = crate::memory::store::reciprocal_rank_fusion(&bp, &vp, 60, self.q.top_k);
        if !merged_s.is_empty() {
            let memories = self.store.fetch_by_ids(&merged_s).await?;
            // Use escalating threshold — we're digging deeper
            let memories = apply_decay_filter(memories, now, ESCALATING_THRESHOLD);
            if !memories.is_empty() {
                let ids = id_strings(&memories);
                let trace = self.store.write_trace(self.q, &ids, RetrievalTier::FullContext).await.ok();
                return Ok(RecallOutcome::Found(RecallResult {
                    memories,
                    trace_id:  trace.and_then(|t| t.id),
                    tier_used: RetrievalTier::FullContext,
                    candidates: bp.len() + vp.len(),
                }));
            }
        }

        // ----------------------------------------------------------------
        // Tier 4: temporal expansion — last 7 days, last 30 days, last 90 days
        // ----------------------------------------------------------------
        debug!("escalating recall tier 4: temporal expansion");
        for days_back in [7i64, 30, 90, 365] {
            let window_start = now - Duration::days(days_back);
            let memories = self.store.memories_valid_at(
                &self.q.agent_id,
                window_start,
                self.q.categories.clone(),
            ).await?;

            // Filter by query relevance using BM25 text match if possible
            let relevant: Vec<Memory> = memories.into_iter()
                .filter(|m| {
                    let ec = effective_confidence(m, now);
                    ec >= ESCALATING_THRESHOLD &&
                    content_matches(&m.content, &self.q.query_text)
                })
                .take(self.q.top_k)
                .collect();

            if !relevant.is_empty() {
                debug!("temporal expansion found {} memories going back {} days", relevant.len(), days_back);
                let ids = id_strings(&relevant);
                let trace = self.store.write_trace(self.q, &ids, RetrievalTier::FullContext).await.ok();
                return Ok(RecallOutcome::Found(RecallResult {
                    memories:  relevant,
                    trace_id:  trace.and_then(|t| t.id),
                    tier_used: RetrievalTier::FullContext,
                    candidates: ids.len(),
                }));
            }
        }

        // ----------------------------------------------------------------
        // Tier 5: scope relaxation — try all scopes
        // ----------------------------------------------------------------
        debug!("escalating recall tier 5: scope relaxation");
        let mut q_wide = self.q.clone();
        q_wide.scope = None; // remove scope filter
        q_wide.session_id = None; // remove session filter
        q_wide.include_superseded = true;
        q_wide.min_confidence = 0.0;

        let (bm25_w, vec_w) = tokio::join!(
            self.store.bm25_search(&q_wide),
            self.store.vector_search(&q_wide),
        );
        let bm25_w = bm25_w.unwrap_or_default();
        let vec_w  = vec_w.unwrap_or_default();

        let bwp: Vec<(String, f32)> = bm25_w.iter()
            .filter_map(|(m, s)| m.id.as_ref().map(|id| (id.key().to_string(), *s)))
            .collect();
        let vwp: Vec<(String, f32)> = vec_w.iter()
            .filter_map(|(m, s)| m.id.as_ref().map(|id| (id.key().to_string(), *s)))
            .collect();

        let merged_w = crate::memory::store::reciprocal_rank_fusion(&bwp, &vwp, 60, self.q.top_k);
        if !merged_w.is_empty() {
            let memories = self.store.fetch_by_ids(&merged_w).await?;
            let memories = apply_decay_filter(memories, now, ESCALATING_THRESHOLD);
            if !memories.is_empty() {
                let ids = id_strings(&memories);
                let trace = self.store.write_trace(self.q, &ids, RetrievalTier::FullContext).await.ok();
                return Ok(RecallOutcome::Found(RecallResult {
                    memories,
                    trace_id:  trace.and_then(|t| t.id),
                    tier_used: RetrievalTier::FullContext,
                    candidates: bwp.len() + vwp.len(),
                }));
            }
        }

        // ----------------------------------------------------------------
        // All tiers exhausted → write gap probe, return Gap
        // ----------------------------------------------------------------
        info!("escalating recall: all tiers exhausted for agent {} query='{}'",
            self.q.agent_id, self.q.query_text);

        let gap = self.store.create_gap_probe(GapProbeInput {
            agent_id:             self.q.agent_id.clone(),
            session_id:           self.q.session_id.clone(),
            query_text:           self.q.query_text.clone(),
            human_insistence:     self.human_insistence.clone(),
            tiers_tried:          vec![1, 2, 3, 4, 5],
            searched_superseded:  true,
            searched_temporal:    true,
            searched_wider_scope: true,
        }).await?;

        Ok(RecallOutcome::Gap(gap))
    }
}

// ---------------------------------------------------------------------------
// Episodic replay
//
// Human says: "we talked about this on Tuesday around 3pm"
// Agent: find session(s) in that window → load ALL memories → reconstruct thread
// ---------------------------------------------------------------------------

pub struct EpisodicReplay<'a> {
    store: &'a Store,
}

impl<'a> EpisodicReplay<'a> {
    pub fn new(store: &'a Store) -> Self {
        Self { store }
    }

    /// Find sessions matching a time anchor and replay the best match.
    ///
    /// anchor can be:
    ///   - ISO datetime string: "2026-05-20T15:00:00Z"
    ///   - Natural description: "last Tuesday" (caller resolves to DateTime range)
    ///   - session_id directly
    pub async fn replay_by_time(
        &self,
        agent_id: &str,
        window_start: DateTime<Utc>,
        window_end: DateTime<Utc>,
        topic_hint: Option<String>,
        gap_probe_id: Option<RecordId>,
    ) -> Result<Option<ReplayedEpisode>> {
        // Find sessions that overlap the time window
        let sessions = self.store.sessions_in_window(
            agent_id,
            window_start,
            window_end,
        ).await?;

        if sessions.is_empty() {
            debug!("episodic replay: no sessions found in window {} → {}",
                window_start, window_end);
            return Ok(None);
        }

        // If topic hint provided, score sessions by topic relevance
        let best_session = if let Some(ref topic) = topic_hint {
            sessions.into_iter()
                .max_by_key(|s| {
                    let topics = s.topics.as_deref().unwrap_or(&[]);
                    let score: usize = topics.iter()
                        .filter(|t| topic.to_lowercase().contains(t.to_lowercase().as_str()))
                        .count();
                    score
                })
                .unwrap() // sessions is non-empty
        } else {
            sessions.into_iter().next().unwrap()
        };

        let episode = self.replay_session(
            agent_id,
            &best_session.session_id,
            gap_probe_id,
        ).await?;

        Ok(Some(episode))
    }

    /// Load all memories from a session_id, ordered chronologically.
    /// Reconstruct the conversation thread.
    /// Load into active_episode table (one row per agent).
    pub async fn replay_session(
        &self,
        agent_id:     &str,
        session_id:   &str,
        gap_probe_id: Option<RecordId>,
    ) -> Result<ReplayedEpisode> {
        info!("replaying session {} for agent {}", session_id, agent_id);

        // Load ALL memories from this session, ordered by known_time
        let memories = self.store.session_memories(agent_id, session_id).await?;

        if memories.is_empty() {
            return Ok(ReplayedEpisode {
                session_id:   session_id.to_string(),
                started_at:   Utc::now(),
                ended_at:     Utc::now(),
                memories:     vec![],
                thread_text:  format!("[session {} — no memories found]", session_id),
                token_count:  0,
                gap_probe_id,
            });
        }

        let started_at = memories.first()
            .and_then(|m| m.known_time)
            .unwrap_or_else(Utc::now);
        let ended_at = memories.last()
            .and_then(|m| m.known_time)
            .unwrap_or_else(Utc::now);

        // Reconstruct conversation thread
        let thread_text = reconstruct_thread(&memories, started_at);
        let token_count = thread_text.split_whitespace().count();

        // Store as active_episode
        let memory_ids: Vec<RecordId> = memories.iter()
            .filter_map(|m| m.id.clone())
            .collect();

        self.store.upsert_active_episode(ActiveEpisodeInput {
            agent_id:         agent_id.to_string(),
            replayed_session: session_id.to_string(),
            started_at,
            ended_at,
            memories:         memory_ids,
            thread_text:      thread_text.clone(),
            token_count:      token_count as i64,
            gap_probe_id:     gap_probe_id.clone(),
        }).await?;

        // Mark the gap probe as resolved if we have one
        if let Some(ref gp_id) = gap_probe_id {
            self.store.resolve_gap_probe(gp_id, session_id).await?;
        }

        info!("episode replayed: {} memories, {} tokens, session {}",
            memories.len(), token_count, session_id);

        Ok(ReplayedEpisode {
            session_id: session_id.to_string(),
            started_at,
            ended_at,
            memories,
            thread_text,
            token_count,
            gap_probe_id,
        })
    }
}

// ---------------------------------------------------------------------------
// Thread reconstruction
//
// Takes memories ordered by time and builds a readable conversation thread.
// This is what gets injected into active context when a session is replayed.
// ---------------------------------------------------------------------------

fn reconstruct_thread(memories: &[Memory], session_start: DateTime<Utc>) -> String {
    let mut parts = vec![
        format!("=== Replayed session from {} ===", session_start.format("%Y-%m-%d %H:%M UTC")),
    ];

    for mem in memories {
        let time_offset = mem.known_time
            .map(|t| {
                let mins = (t - session_start).num_minutes();
                if mins < 60 {
                    format!("+{}m", mins)
                } else {
                    format!("+{}h{}m", mins / 60, mins % 60)
                }
            })
            .unwrap_or_else(|| "?".to_string());

        let source = match mem.source_kind {
            SourceKind::UserTurn   => "human",
            SourceKind::AgentTurn  => "agent",
            SourceKind::ToolOutput => "tool",
            _                      => "system",
        };

        let category = match mem.category {
            MemoryCategory::Episodic    => "",
            MemoryCategory::Identity    => " [identity]",
            MemoryCategory::Knowledge   => " [knowledge]",
            MemoryCategory::Context     => " [context]",
            MemoryCategory::Instruction => " [instruction]",
            MemoryCategory::Uncertainty => " [uncertain]",
        };

        parts.push(format!("[{}] {}{}: {}", time_offset, source, category, mem.content));
    }

    parts.push("=== End of replayed session ===".to_string());
    parts.join("\n")
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn apply_decay_filter(
    memories: Vec<Memory>,
    now: DateTime<Utc>,
    threshold: f64,
) -> Vec<Memory> {
    memories.into_iter()
        .filter(|m| effective_confidence(m, now) >= threshold)
        .collect()
}

fn id_strings(memories: &[Memory]) -> Vec<String> {
    memories.iter()
        .filter_map(|m| m.id.as_ref().map(|id| id.key().to_string()))
        .collect()
}

/// Simple keyword overlap check for temporal expansion filtering.
fn content_matches(content: &str, query: &str) -> bool {
    if query.is_empty() { return true; }
    let content_lower = content.to_lowercase();
    query.split_whitespace()
        .filter(|w| w.len() > 3) // skip short words
        .any(|word| content_lower.contains(&word.to_lowercase()))
}

// ---------------------------------------------------------------------------
// Input types for store methods
// ---------------------------------------------------------------------------

#[derive(Debug, Clone)]
pub struct GapProbeInput {
    pub agent_id:             String,
    pub session_id:           Option<String>,
    pub query_text:           String,
    pub human_insistence:     Option<String>,
    pub tiers_tried:          Vec<i32>,
    pub searched_superseded:  bool,
    pub searched_temporal:    bool,
    pub searched_wider_scope: bool,
}

#[derive(Debug, Clone)]
pub struct ActiveEpisodeInput {
    pub agent_id:         String,
    pub replayed_session: String,
    pub started_at:       DateTime<Utc>,
    pub ended_at:         DateTime<Utc>,
    pub memories:         Vec<RecordId>,
    pub thread_text:      String,
    pub token_count:      i64,
    pub gap_probe_id:     Option<RecordId>,
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct SessionIndexRecord {
    pub session_id:   String,
    pub agent_id:     String,
    pub started_at:   DateTime<Utc>,
    pub ended_at:     DateTime<Utc>,
    pub summary:      Option<String>,
    pub topics:       Option<Vec<String>>,
    pub memory_count: i64,
}
