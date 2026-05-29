use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use surrealdb::RecordId;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum MemoryCategory {
    Episodic,
    Identity,
    Knowledge,
    Context,
    Instruction,
    Uncertainty,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum SourceKind {
    AgentTurn,
    UserTurn,
    Document,
    Reflection,
    Elaboration,
    Consolidation,
    ToolOutput,
    External,
}

impl Default for SourceKind {
    fn default() -> Self { Self::AgentTurn }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum MemoryScope {
    Agent,
    Team,
    Org,
    Project,
}

impl Default for MemoryScope {
    fn default() -> Self { Self::Agent }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum EdgeKind {
    RelatedTo,
    Updates,
    Contradicts,
    CausedBy,
    PartOf,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DecisionStatus {
    Pending,
    Success,
    Failed,
    Rejected,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RetrievalTier {
    DirectLookup  = 1,
    ResponseReuse = 2,
    Hybrid        = 3,
    FullContext    = 4,
}

impl Default for RetrievalTier {
    fn default() -> Self { Self::Hybrid }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum WorkingMemoryLayer {
    IdentityContext,
    IntradaySynthesis,
    DailyRollup,
    CrossAgentMap,
    KnowledgeBrief,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum EvolutionStatus {
    Pending,
    Processing,
    Done,
    Skipped,
}

// ---------------------------------------------------------------------------
// Memory record
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Memory {
    pub id:               Option<RecordId>,
    pub category:         MemoryCategory,
    pub content:          String,
    pub summary:          Option<String>,

    // Ownership
    pub agent_id:         String,
    pub session_id:       Option<String>,
    pub scope:            MemoryScope,

    // Tri-temporal
    pub known_time:       Option<DateTime<Utc>>,
    pub valid_time_start: Option<DateTime<Utc>>,
    pub valid_time_end:   Option<DateTime<Utc>>,

    // Provenance
    pub source_kind:      SourceKind,
    pub source_ref:       Option<String>,
    pub source_trust:     f64,
    pub derived_from:     Option<Vec<RecordId>>,

    // Calibration
    pub confidence:       f64,
    pub importance:       f64,

    // Supersession
    pub superseded:       bool,
    pub superseded_at:    Option<DateTime<Utc>>,
    pub superseded_by:    Option<RecordId>,

    // Evolution
    pub keywords:         Option<Vec<String>>,
    pub tags:             Option<Vec<String>>,
    pub evolved_at:       Option<DateTime<Utc>>,

    // Vector
    pub embedding:        Option<Vec<f32>>,

    pub created_at:       Option<DateTime<Utc>>,
    pub updated_at:       Option<DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Input types
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryInput {
    pub category:         MemoryCategory,
    pub content:          String,
    pub summary:          Option<String>,
    pub agent_id:         String,
    pub session_id:       Option<String>,
    pub scope:            Option<MemoryScope>,
    pub valid_time_start: Option<DateTime<Utc>>,
    pub valid_time_end:   Option<DateTime<Utc>>,
    pub source_kind:      Option<SourceKind>,
    pub source_ref:       Option<String>,
    pub source_trust:     Option<f64>,
    pub derived_from:     Option<Vec<String>>,
    pub confidence:       Option<f64>,
    pub importance:       Option<f64>,
    pub keywords:         Option<Vec<String>>,
    pub tags:             Option<Vec<String>>,
    pub embedding:        Option<Vec<f32>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SupersedeInput {
    pub old_memory_id:  String,
    pub new_content:    String,
    pub source_kind:    Option<SourceKind>,
    pub source_ref:     Option<String>,
    pub confidence:     Option<f64>,
    pub embedding:      Option<Vec<f32>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecallQuery {
    pub agent_id:           String,
    pub query_text:         String,
    pub query_embedding:    Option<Vec<f32>>,
    pub categories:         Option<Vec<MemoryCategory>>,
    pub scope:              Option<MemoryScope>,
    pub session_id:         Option<String>,
    pub include_superseded: bool,
    pub tier:               RetrievalTier,
    pub top_k:              usize,
    pub min_confidence:     f64,
    pub valid_at:           Option<DateTime<Utc>>,
}

impl Default for RecallQuery {
    fn default() -> Self {
        Self {
            agent_id:           String::new(),
            query_text:         String::new(),
            query_embedding:    None,
            categories:         None,
            scope:              None,
            session_id:         None,
            include_superseded: false,
            tier:               RetrievalTier::Hybrid,
            top_k:              10,
            min_confidence:     0.0,
            valid_at:           None,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RecallResult {
    pub memories:   Vec<Memory>,
    pub trace_id:   Option<RecordId>,
    pub tier_used:  RetrievalTier,
    pub candidates: usize,
}

// ---------------------------------------------------------------------------
// Graph edge
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemEdge {
    pub id:         Option<RecordId>,
    pub r#in:       RecordId,
    pub out:        RecordId,
    pub kind:       EdgeKind,
    pub weight:     f64,
    pub created_at: Option<DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Retrieval trace
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrievalTrace {
    pub id:              Option<RecordId>,
    pub agent_id:        String,
    pub session_id:      Option<String>,
    pub query_text:      String,
    pub query_embedding: Option<Vec<f32>>,
    pub tier:            i64,
    pub result_ids:      Vec<RecordId>,
    pub result_scores:   Option<Vec<f32>>,
    pub useful:          Option<bool>,
    pub correction:      Option<bool>,
    pub created_at:      Option<DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Decision trace
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionTrace {
    pub id:          Option<RecordId>,
    pub run_id:      String,
    pub step_id:     String,
    pub agent_id:    String,
    pub actor:       Option<String>,
    pub action:      String,
    pub input:       serde_json::Value,
    pub output:      serde_json::Value,
    pub status:      DecisionStatus,
    pub memory_refs: Option<Vec<RecordId>>,
    pub created_at:  Option<DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Working memory
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkingMemory {
    pub id:               Option<RecordId>,
    pub agent_id:         String,
    pub layer:            WorkingMemoryLayer,
    pub content:          String,
    pub source_memories:  Option<Vec<RecordId>>,
    pub valid_date:       Option<DateTime<Utc>>,
    pub token_count:      Option<i64>,
    pub created_at:       Option<DateTime<Utc>>,
    pub updated_at:       Option<DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Evolution queue
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvolutionJob {
    pub id:            Option<RecordId>,
    pub new_memory_id: RecordId,
    pub agent_id:      String,
    pub category:      String,
    pub status:        EvolutionStatus,
    pub processed_at:  Option<DateTime<Utc>>,
    pub created_at:    Option<DateTime<Utc>>,
}
