use anyhow::Result;
use rmcp::{
    ServerHandler, ServiceExt,
    model::{
        CallToolResult, Content, Implementation, ProtocolVersion,
        ServerCapabilities, ServerInfo, Tool,
    },
    tool, tool_handler, tool_router,
};
use serde_json::{json, Value};
use tracing::info;

use crate::memory::{
    conflict::{ConflictInput, ConflictType},
    gap::RecallOutcome,
    service::MemoryService,
    types::*,
};

// ---------------------------------------------------------------------------
// AgentMemoryMcp — MCP server handler
//
// Six tools (Spectron surface):
//   remember  → create memory
//   recall    → hybrid retrieval
//   update    → supersede-not-overwrite
//   forget    → soft forget
//   reflect   → on-demand synthesis (stub — caller injects LLM)
//   inspect   → retrieval trace + supersession lineage
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct AgentMemoryMcp {
    service: MemoryService,
}

impl AgentMemoryMcp {
    pub fn new(service: MemoryService) -> Self {
        Self { service }
    }
}

#[tool_router]
impl AgentMemoryMcp {
    /// Store a new memory for an agent.
    #[tool(description = "Store a new memory. Category: episodic|identity|knowledge|context|instruction|uncertainty")]
    async fn remember(
        &self,
        #[tool(param)] agent_id: String,
        #[tool(param)] content: String,
        #[tool(param)] category: String,
        #[tool(param)] session_id: Option<String>,
        #[tool(param)] importance: Option<f64>,
        #[tool(param)] confidence: Option<f64>,
        #[tool(param)] keywords: Option<Vec<String>>,
        #[tool(param)] tags: Option<Vec<String>>,
    ) -> Result<CallToolResult, rmcp::Error> {
        let cat = parse_category(&category);

        let input = MemoryInput {
            agent_id,
            content,
            category: cat,
            session_id,
            importance,
            confidence,
            keywords,
            tags,
            summary: None,
            scope: None,
            valid_time_start: None,
            valid_time_end: None,
            source_kind: None,
            source_ref: None,
            source_trust: None,
            derived_from: None,
            embedding: None,
        };

        match self.service.remember(input).await {
            Ok(mem) => Ok(CallToolResult::success(vec![Content::text(
                serde_json::to_string(&json!({
                    "id": mem.id.as_ref().map(|id| id.to_string()),
                    "category": serde_json::to_value(&mem.category).unwrap_or_default(),
                    "created_at": mem.created_at,
                })).unwrap_or_default()
            )])),
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

    /// Recall memories using hybrid retrieval (BM25 + vector + RRF).
    #[tool(description = "Retrieve memories using hybrid search. Returns top-k relevant memories with trace.")]
    async fn recall(
        &self,
        #[tool(param)] agent_id: String,
        #[tool(param)] query: String,
        #[tool(param)] top_k: Option<i64>,
        #[tool(param)] categories: Option<Vec<String>>,
        #[tool(param)] session_id: Option<String>,
        #[tool(param)] min_confidence: Option<f64>,
    ) -> Result<CallToolResult, rmcp::Error> {
        let cats = categories.map(|cs| cs.iter().map(|c| parse_category(c)).collect());

        let q = RecallQuery {
            agent_id,
            query_text: query,
            top_k: top_k.unwrap_or(10) as usize,
            categories: cats,
            session_id,
            min_confidence: min_confidence.unwrap_or(0.0),
            tier: RetrievalTier::Hybrid,
            ..Default::default()
        };

        match self.service.recall(q).await {
            Ok(result) => {
                let mems: Vec<Value> = result.memories.iter().map(|m| json!({
                    "id":         m.id.as_ref().map(|id| id.to_string()),
                    "category":   serde_json::to_value(&m.category).unwrap_or_default(),
                    "content":    m.content,
                    "confidence": m.confidence,
                    "importance": m.importance,
                    "known_time": m.known_time,
                    "source_kind": serde_json::to_value(&m.source_kind).unwrap_or_default(),
                    "superseded": m.superseded,
                })).collect();

                Ok(CallToolResult::success(vec![Content::text(
                    serde_json::to_string(&json!({
                        "memories":   mems,
                        "trace_id":   result.trace_id.as_ref().map(|id| id.to_string()),
                        "tier":       result.tier_used as i64,
                        "candidates": result.candidates,
                    })).unwrap_or_default()
                )]))
            }
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

    /// Update a memory using supersede-not-overwrite (Spectron model).
    /// Old memory is preserved with valid_time_end set. New memory created with derived_from.
    #[tool(description = "Supersede a memory. Old record is preserved with valid_time_end set. New record created.")]
    async fn update(
        &self,
        #[tool(param)] memory_id: String,
        #[tool(param)] new_content: String,
        #[tool(param)] confidence: Option<f64>,
    ) -> Result<CallToolResult, rmcp::Error> {
        let input = SupersedeInput {
            old_memory_id: memory_id,
            new_content,
            confidence,
            source_kind: None,
            source_ref: None,
            embedding: None,
        };

        match self.service.update(input).await {
            Ok((old, new)) => Ok(CallToolResult::success(vec![Content::text(
                serde_json::to_string(&json!({
                    "superseded": old.id.as_ref().map(|id| id.to_string()),
                    "new": new.id.as_ref().map(|id| id.to_string()),
                    "superseded_at": old.superseded_at,
                })).unwrap_or_default()
            )])),
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

    /// Soft-forget a memory. Sets valid_time_end = now. History remains queryable.
    #[tool(description = "Forget a memory (soft). Sets valid_time_end. History preserved. Use purge=true only for GDPR.")]
    async fn forget(
        &self,
        #[tool(param)] memory_id: String,
        #[tool(param)] purge: Option<bool>,
    ) -> Result<CallToolResult, rmcp::Error> {
        let result = if purge.unwrap_or(false) {
            self.service.purge(&memory_id).await
        } else {
            self.service.forget(&memory_id).await
        };

        match result {
            Ok(()) => Ok(CallToolResult::success(vec![Content::text(
                json!({"forgotten": memory_id, "purged": purge.unwrap_or(false)}).to_string()
            )])),
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

    /// On-demand synthesis: reflect over retrieved context.
    /// Returns assembled working memory layers for the agent.
    #[tool(description = "Reflect: return assembled Cortex working memory layers for prompt injection.")]
    async fn reflect(
        &self,
        #[tool(param)] agent_id: String,
    ) -> Result<CallToolResult, rmcp::Error> {
        match self.service.context(&agent_id).await {
            Ok(layers) => {
                let result: Vec<Value> = layers.iter().map(|wm| json!({
                    "layer":       serde_json::to_value(&wm.layer).unwrap_or_default(),
                    "content":     wm.content,
                    "token_count": wm.token_count,
                    "updated_at":  wm.updated_at,
                })).collect();

                Ok(CallToolResult::success(vec![Content::text(
                    serde_json::to_string(&result).unwrap_or_default()
                )]))
            }
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

    /// Inspect: retrieval trace feedback or supersession lineage.
    #[tool(description = "Inspect memory history (supersession lineage) or submit trace feedback.")]
    async fn inspect(
        &self,
        #[tool(param)] memory_id: Option<String>,
        #[tool(param)] trace_id: Option<String>,
        #[tool(param)] useful: Option<bool>,
        #[tool(param)] correction: Option<bool>,
    ) -> Result<CallToolResult, rmcp::Error> {
        // Trace feedback
        if let Some(tid) = trace_id {
            match self.service.feedback(&tid, useful, correction).await {
                Ok(()) => return Ok(CallToolResult::success(vec![Content::text(
                    json!({"feedback_recorded": tid}).to_string()
                )])),
                Err(e) => return Err(rmcp::Error::internal_error(e.to_string(), None)),
            }
        }

        // Supersession lineage
        if let Some(mid) = memory_id {
            match self.service.history(&mid).await {
                Ok(chain) => {
                    let result: Vec<Value> = chain.iter().map(|m| json!({
                        "id":           m.id.as_ref().map(|id| id.to_string()),
                        "content":      m.content,
                        "superseded":   m.superseded,
                        "superseded_at": m.superseded_at,
                        "superseded_by": m.superseded_by.as_ref().map(|id| id.to_string()),
                        "known_time":   m.known_time,
                    })).collect();

                    return Ok(CallToolResult::success(vec![Content::text(
                        serde_json::to_string(&result).unwrap_or_default()
                    )]));
                }
                Err(e) => return Err(rmcp::Error::internal_error(e.to_string(), None)),
            }
        }

        Err(rmcp::Error::invalid_params("provide memory_id or trace_id", None))
    }
    /// Try to recall something, trying all tiers before giving up.
    /// If nothing found, returns a gap probe with a suggested prompt for the human.
    /// Pass human_insistence="I told you about X last week" for a better gap message.
    #[tool(description = "Recall with full escalation. Returns found memories OR a gap probe asking the human for a time anchor.")]
    async fn recall_or_gap(
        &self,
        #[tool(param)] agent_id: String,
        #[tool(param)] query: String,
        #[tool(param)] human_insistence: Option<String>,
        #[tool(param)] top_k: Option<i64>,
        #[tool(param)] categories: Option<Vec<String>>,
    ) -> Result<CallToolResult, rmcp::Error> {
        let cats = categories.map(|cs| cs.iter().map(|c| parse_category(c)).collect());
        let q = RecallQuery {
            agent_id,
            query_text: query,
            top_k: top_k.unwrap_or(10) as usize,
            categories: cats,
            tier: RetrievalTier::Hybrid,
            ..Default::default()
        };

        match self.service.recall_or_gap(q, human_insistence).await {
            Ok(RecallOutcome::Found(result)) => {
                let mems: Vec<Value> = result.memories.iter().map(|m| json!({
                    "id":         m.id.as_ref().map(|id| id.to_string()),
                    "category":   serde_json::to_value(&m.category).unwrap_or_default(),
                    "content":    m.content,
                    "confidence": m.confidence,
                    "known_time": m.known_time,
                    "epistemic_status": serde_json::to_value(&m.epistemic_status).unwrap_or_default(),
                    "superseded": m.superseded,
                })).collect();

                Ok(CallToolResult::success(vec![Content::text(
                    json!({
                        "outcome": "found",
                        "memories": mems,
                        "tier": result.tier_used as i64,
                        "candidates": result.candidates,
                    }).to_string()
                )]))
            }
            Ok(RecallOutcome::Gap(gap)) => {
                Ok(CallToolResult::success(vec![Content::text(
                    json!({
                        "outcome": "gap",
                        "gap_probe_id": gap.id.as_ref().map(|id| id.to_string()),
                        "tiers_tried": gap.tiers_tried,
                        "searched_superseded": gap.searched_superseded,
                        "searched_temporal": gap.searched_temporal,
                        "suggested_prompt": gap.suggested_prompt,
                    }).to_string()
                )]))
            }
            Ok(RecallOutcome::EpisodeReplayed(ep)) => {
                Ok(CallToolResult::success(vec![Content::text(
                    json!({
                        "outcome": "episode_replayed",
                        "session_id": ep.session_id,
                        "started_at": ep.started_at,
                        "ended_at": ep.ended_at,
                        "memory_count": ep.memories.len(),
                        "token_count": ep.token_count,
                        "thread_preview": &ep.thread_text[..ep.thread_text.len().min(500)],
                    }).to_string()
                )]))
            }
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

    /// Replay a complete past session into active memory.
    /// Human provides a time anchor (window_start + window_end as ISO strings).
    /// The full conversation thread is loaded into active context.
    #[tool(description = "Replay a past session. Human gave a time anchor. Loads the complete episode into active memory.")]
    async fn replay_episode(
        &self,
        #[tool(param)] agent_id: String,
        #[tool(param)] window_start: String,
        #[tool(param)] window_end: String,
        #[tool(param)] topic_hint: Option<String>,
        #[tool(param)] gap_probe_id: Option<String>,
    ) -> Result<CallToolResult, rmcp::Error> {
        use chrono::DateTime;

        let start = DateTime::parse_from_rfc3339(&window_start)
            .map(|d| d.with_timezone(&chrono::Utc))
            .map_err(|e| rmcp::Error::invalid_params(format!("window_start: {}", e), None))?;

        let end = DateTime::parse_from_rfc3339(&window_end)
            .map(|d| d.with_timezone(&chrono::Utc))
            .map_err(|e| rmcp::Error::invalid_params(format!("window_end: {}", e), None))?;

        let gp_id = gap_probe_id.map(|id| {
            surrealdb::RecordId::from_table_key("gap_probe", id.as_str())
        });

        match self.service.replay_by_window(&agent_id, start, end, topic_hint, gp_id).await {
            Ok(Some(ep)) => Ok(CallToolResult::success(vec![Content::text(
                json!({
                    "outcome": "episode_replayed",
                    "session_id": ep.session_id,
                    "started_at": ep.started_at,
                    "ended_at": ep.ended_at,
                    "memory_count": ep.memories.len(),
                    "token_count": ep.token_count,
                    "thread_text": ep.thread_text,
                }).to_string()
            )])),
            Ok(None) => Ok(CallToolResult::success(vec![Content::text(
                json!({
                    "outcome": "no_session_found",
                    "message": "No sessions found in the provided time window. The human may have more specific context.",
                }).to_string()
            )])),
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

    /// Resolve a conflict between what the agent has and what the human says.
    /// conflict_type: "misinterpretation" | "agent_stands_firm" | "factual_contradiction"
    ///
    /// misinterpretation   → human says agent got the interpretation wrong
    ///                       agent accepts, versions the interpretation
    /// agent_stands_firm   → human says agent said X, agent's log says Y
    ///                       agent shows its exact log, does not update
    /// factual_contradiction → human claims a number/fact differs from chat log
    ///                       agent shows exact line, halts that reasoning thread
    #[tool(description = "Resolve conflict. Types: misinterpretation | agent_stands_firm | factual_contradiction. Returns agent_response and halt_reasoning flag.")]
    async fn conflict_resolve(
        &self,
        #[tool(param)] agent_id: String,
        #[tool(param)] session_id: Option<String>,
        #[tool(param)] conflict_type: String,
        #[tool(param)] human_statement: String,
        #[tool(param)] prior_memory_id: Option<String>,
        #[tool(param)] correct_interpretation: Option<String>,
    ) -> Result<CallToolResult, rmcp::Error> {
        let ct = match conflict_type.as_str() {
            "misinterpretation"    => ConflictType::Misinterpretation,
            "agent_stands_firm"    => ConflictType::AgentStandsFirm,
            "factual_contradiction" => ConflictType::FactualContradiction,
            other => return Err(rmcp::Error::invalid_params(
                format!("unknown conflict_type: {}", other), None
            )),
        };

        let input = ConflictInput {
            agent_id,
            session_id,
            conflict_type: ct,
            human_statement,
            prior_memory_id,
            correct_interpretation,
        };

        match self.service.resolve_conflict(input).await {
            Ok(trace) => Ok(CallToolResult::success(vec![Content::text(
                serde_json::to_string(&json!({
                    "agent_response":        trace.agent_response,
                    "halt_reasoning":        trace.halt_reasoning,
                    "resolution":            format!("{:?}", trace.resolution),
                    "interpretation_version": trace.interpretation_version,
                    "calibration_reasoning": trace.calibration_reasoning,
                    "prior_verbatim":        trace.prior_verbatim,
                    "prior_known_time":      trace.prior_known_time,
                })).unwrap_or_default()
            )])),
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

    /// Show the decision log — recent conflict traces for an agent.
    /// Use this to show the human what decisions were made and why.
    #[tool(description = "Show decision log. Returns recent conflict resolutions with reasoning, prior records, and what the agent said.")]
    async fn decision_log(
        &self,
        #[tool(param)] agent_id: String,
        #[tool(param)] limit: Option<i64>,
    ) -> Result<CallToolResult, rmcp::Error> {
        match self.service.conflict_history(&agent_id, limit.unwrap_or(20) as usize).await {
            Ok(rows) => {
                let entries: Vec<Value> = rows.iter().map(|r| json!({
                    "id":                   r.id.as_ref().map(|id| id.to_string()),
                    "conflict_type":        r.conflict_type,
                    "prior_content":        r.prior_content,
                    "prior_verbatim":       r.prior_verbatim,
                    "prior_known_time":     r.prior_known_time,
                    "human_statement":      r.human_statement,
                    "resolution":           r.resolution,
                    "calibration_reasoning": r.calibration_reasoning,
                    "agent_response":       r.agent_response,
                    "halt_reasoning":       r.halt_reasoning,
                    "created_at":           r.created_at,
                })).collect();

                Ok(CallToolResult::success(vec![Content::text(
                    serde_json::to_string(&json!({
                        "count":   entries.len(),
                        "entries": entries,
                    })).unwrap_or_default()
                )]))
            }
            Err(e) => Err(rmcp::Error::internal_error(e.to_string(), None)),
        }
    }

}

#[tool_handler]
impl ServerHandler for AgentMemoryMcp {
    fn get_info(&self) -> ServerInfo {
        ServerInfo {
            protocol_version: ProtocolVersion::V_2024_11_05,
            capabilities: ServerCapabilities::builder()
                .enable_tools()
                .build(),
            server_info: Implementation {
                name:    "agent-memory".to_string(),
                version: env!("CARGO_PKG_VERSION").to_string(),
            },
            instructions: Some(
                "Agent-Memory: provenance-first, tri-temporal memory layer. \
                 Ten tools: remember, recall, recall_or_gap, update, forget, reflect, inspect, replay_episode, conflict_resolve, decision_log. \
                 Use recall_or_gap when human insists on something not found. Use replay_episode with a time anchor to load full past session."
                    .to_string(),
            ),
        }
    }
}

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

fn parse_category(s: &str) -> MemoryCategory {
    match s {
        "episodic"     => MemoryCategory::Episodic,
        "identity"     => MemoryCategory::Identity,
        "knowledge"    => MemoryCategory::Knowledge,
        "context"      => MemoryCategory::Context,
        "instruction"  => MemoryCategory::Instruction,
        "uncertainty"  => MemoryCategory::Uncertainty,
        _              => MemoryCategory::Knowledge,
    }
}

/// Start the MCP server on stdio (Claude Desktop / Claude Code compatible).
pub async fn serve_stdio(service: MemoryService) -> Result<()> {
    info!("agent-memory MCP server starting on stdio");
    let handler = AgentMemoryMcp::new(service);
    let server = handler.serve(rmcp::transport::stdio()).await?;
    server.waiting().await?;
    Ok(())
}
