/// Extension methods on Store for gap protocol, session index, and decay reinforcement.
/// This file is included via `mod store_gap;` in store.rs — keeping store.rs clean.

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use surrealdb::RecordId;

use crate::memory::{
    decay::{next_reinforcement_count, reinforced_confidence},
    gap::{ActiveEpisodeInput, GapProbeInput, GapProbeRecord, SessionIndexRecord},
    store::Store,
    types::Memory,
};

impl Store {
    // -----------------------------------------------------------------------
    // Reinforcement — reset decay, update confidence
    // -----------------------------------------------------------------------

    /// Mark a memory as reinforced. Called when a memory is recalled and useful.
    /// Resets decay by updating last_reinforced_at.
    /// Nudges confidence upward asymptotically.
    pub async fn reinforce_memory(&self, memory_id: &str) -> Result<()> {
        let id = RecordId::from_table_key("memory", memory_id);

        // Fetch current values
        let mem: Option<Memory> = self.db.select(id.clone()).await?;
        let mem = match mem {
            Some(m) => m,
            None => return Ok(()),
        };

        let new_count = next_reinforcement_count(mem.reinforcement_count);
        let new_confidence = reinforced_confidence(mem.confidence);

        self.db.query(
            r#"
            UPDATE $id SET
                last_reinforced_at  = time::now(),
                reinforcement_count = $count,
                confidence          = $confidence,
                updated_at          = time::now();
            "#,
        )
        .bind(("id",         id))
        .bind(("count",      new_count))
        .bind(("confidence", new_confidence))
        .await?;

        Ok(())
    }

    // -----------------------------------------------------------------------
    // Gap probe
    // -----------------------------------------------------------------------

    pub async fn create_gap_probe(&self, input: GapProbeInput) -> Result<GapProbeRecord> {
        let mut res = self.db.query(
            r#"
            CREATE gap_probe SET
                agent_id              = $agent_id,
                session_id            = $session_id,
                query_text            = $query_text,
                human_insistence      = $human_insistence,
                tiers_tried           = $tiers_tried,
                searched_superseded   = $searched_superseded,
                searched_temporal     = $searched_temporal,
                searched_wider_scope  = $searched_wider_scope,
                resolved              = false,
                created_at            = time::now()
            RETURN *;
            "#,
        )
        .bind(("agent_id",             input.agent_id.clone()))
        .bind(("session_id",           input.session_id.clone()))
        .bind(("query_text",           input.query_text.clone()))
        .bind(("human_insistence",     input.human_insistence.clone()))
        .bind(("tiers_tried",          input.tiers_tried.clone()))
        .bind(("searched_superseded",  input.searched_superseded))
        .bind(("searched_temporal",    input.searched_temporal))
        .bind(("searched_wider_scope", input.searched_wider_scope))
        .await?;

        // Return the gap probe record
        #[derive(serde::Deserialize)]
        struct Raw {
            id:                   Option<RecordId>,
            agent_id:             String,
            session_id:           Option<String>,
            query_text:           String,
            human_insistence:     Option<String>,
            tiers_tried:          Vec<i32>,
            searched_superseded:  bool,
            searched_temporal:    bool,
            searched_wider_scope: bool,
        }

        let raw: Option<Raw> = res.take(0)?;
        let raw = raw.context("create_gap_probe returned nothing")?;

        let suggested = build_gap_prompt(&raw.query_text, &raw.human_insistence);

        Ok(GapProbeRecord {
            id:                   raw.id,
            agent_id:             raw.agent_id,
            session_id:           raw.session_id,
            query_text:           raw.query_text,
            human_insistence:     raw.human_insistence,
            tiers_tried:          raw.tiers_tried,
            searched_superseded:  raw.searched_superseded,
            searched_temporal:    raw.searched_temporal,
            searched_wider_scope: raw.searched_wider_scope,
            suggested_prompt:     suggested,
        })
    }

    pub async fn resolve_gap_probe(
        &self,
        gap_probe_id: &RecordId,
        resolved_by_session: &str,
    ) -> Result<()> {
        self.db.query(
            r#"
            UPDATE $id SET
                resolved             = true,
                resolved_at          = time::now(),
                resolved_by_session  = $session;
            "#,
        )
        .bind(("id",      gap_probe_id.clone()))
        .bind(("session", resolved_by_session.to_string()))
        .await?;
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Session index
    // -----------------------------------------------------------------------

    /// Called after each episodic memory write to keep session_index current.
    pub async fn update_session_index(
        &self,
        agent_id:   &str,
        session_id: &str,
        known_time: DateTime<Utc>,
        topics:     Option<Vec<String>>,
    ) -> Result<()> {
        let id = RecordId::from_table_key(
            "session_index",
            format!("{}_{}", agent_id, session_id).as_str(),
        );

        self.db.query(
            r#"
            UPSERT $id SET
                session_id   = $session_id,
                agent_id     = $agent_id,
                started_at   = IF started_at IS NONE OR started_at > $ts THEN $ts ELSE started_at END,
                ended_at     = IF ended_at IS NONE OR ended_at < $ts THEN $ts ELSE ended_at END,
                memory_count = (SELECT count() FROM memory WHERE session_id = $session_id AND agent_id = $agent_id GROUP ALL)[0].count OR 1,
                topics       = IF $topics IS NOT NONE THEN $topics ELSE topics END,
                updated_at   = time::now();
            "#,
        )
        .bind(("id",         id))
        .bind(("session_id", session_id.to_string()))
        .bind(("agent_id",   agent_id.to_string()))
        .bind(("ts",         known_time))
        .bind(("topics",     topics))
        .await?;

        Ok(())
    }

    /// Find sessions whose time window overlaps [window_start, window_end].
    pub async fn sessions_in_window(
        &self,
        agent_id:     &str,
        window_start: DateTime<Utc>,
        window_end:   DateTime<Utc>,
    ) -> Result<Vec<SessionIndexRecord>> {
        let mut res = self.db.query(
            r#"
            SELECT * FROM session_index
            WHERE agent_id = $agent_id
                AND started_at <= $window_end
                AND ended_at   >= $window_start
            ORDER BY started_at DESC;
            "#,
        )
        .bind(("agent_id",     agent_id.to_string()))
        .bind(("window_start", window_start))
        .bind(("window_end",   window_end))
        .await?;

        let sessions: Vec<SessionIndexRecord> = res.take(0)?;
        Ok(sessions)
    }

    /// Load ALL memories from a session, ordered chronologically.
    /// This is the full episode — every episodic, knowledge, context memory
    /// from that session. Used for episode replay.
    pub async fn session_memories(
        &self,
        agent_id:   &str,
        session_id: &str,
    ) -> Result<Vec<Memory>> {
        let mut res = self.db.query(
            r#"
            SELECT * FROM memory
            WHERE agent_id  = $agent_id
                AND session_id = $session_id
            ORDER BY known_time ASC;
            "#,
        )
        .bind(("agent_id",   agent_id.to_string()))
        .bind(("session_id", session_id.to_string()))
        .await?;

        let memories: Vec<Memory> = res.take(0)?;
        Ok(memories)
    }

    // -----------------------------------------------------------------------
    // Active episode
    // -----------------------------------------------------------------------

    /// Upsert the active episode for an agent.
    /// One row per agent — replaces any previous active episode.
    pub async fn upsert_active_episode(&self, input: ActiveEpisodeInput) -> Result<()> {
        let id = RecordId::from_table_key(
            "active_episode",
            input.agent_id.as_str(),
        );

        self.db.query(
            r#"
            UPSERT $id SET
                agent_id         = $agent_id,
                replayed_session = $replayed_session,
                started_at       = $started_at,
                ended_at         = $ended_at,
                memories         = $memories,
                thread_text      = $thread_text,
                token_count      = $token_count,
                gap_probe_id     = $gap_probe_id,
                updated_at       = time::now();
            "#,
        )
        .bind(("id",               id))
        .bind(("agent_id",         input.agent_id))
        .bind(("replayed_session", input.replayed_session))
        .bind(("started_at",       input.started_at))
        .bind(("ended_at",         input.ended_at))
        .bind(("memories",         input.memories))
        .bind(("thread_text",      input.thread_text))
        .bind(("token_count",      input.token_count))
        .bind(("gap_probe_id",     input.gap_probe_id))
        .await?;

        Ok(())
    }

    /// Get the active episode for an agent (if any).
    pub async fn get_active_episode(&self, agent_id: &str) -> Result<Option<ActiveEpisodeRow>> {
        let id = RecordId::from_table_key("active_episode", agent_id);
        let row: Option<ActiveEpisodeRow> = self.db.select(id).await?;
        Ok(row)
    }

    /// Clear active episode when session ends.
    pub async fn clear_active_episode(&self, agent_id: &str) -> Result<()> {
        let id = RecordId::from_table_key("active_episode", agent_id);
        self.db.query("DELETE $id;").bind(("id", id)).await?;
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Helper types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, serde::Deserialize)]
pub struct ActiveEpisodeRow {
    pub agent_id:         String,
    pub replayed_session: String,
    pub started_at:       DateTime<Utc>,
    pub ended_at:         DateTime<Utc>,
    pub thread_text:      String,
    pub token_count:      i64,
    pub gap_probe_id:     Option<RecordId>,
    pub updated_at:       Option<DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Build the suggested prompt for a gap probe
// ---------------------------------------------------------------------------

fn build_gap_prompt(query: &str, insistence: &Option<String>) -> String {
    if let Some(insist) = insistence {
        format!(
            "I don't have '{}' in memory, even after searching everything I have. \
             You mentioned we discussed this — can you give me a hint about when? \
             Even roughly — a day, a topic we were talking about, or what else was \
             happening at the time would help me find it.",
            insist
        )
    } else {
        format!(
            "I don't have anything about '{}' in memory. \
             If we discussed this before, can you tell me roughly when? \
             I can replay that conversation and find what you're referring to.",
            query
        )
    }
}
