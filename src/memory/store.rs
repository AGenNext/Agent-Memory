use std::path::PathBuf;

use anyhow::{Context, Result};
use surrealdb::{
    engine::local::{Db, Mem, RocksDb},
    RecordId, Surreal,
};
use tracing::{debug, info};

use crate::memory::types::*;

const MIGRATION: &str = include_str!("../../migrations/001_memory.surql");
const NS: &str = "agnxxt";
const DB: &str = "agent_memory";

// ---------------------------------------------------------------------------
// Store — wraps the embedded SurrealDB engine
// No network. No auth. In-process.
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct Store {
    db: Surreal<Db>,
}

impl Store {
    /// Boot with RocksDB persistence at `data_dir`.
    pub async fn open(data_dir: PathBuf) -> Result<Self> {
        std::fs::create_dir_all(&data_dir)
            .with_context(|| format!("create data dir {:?}", data_dir))?;

        let db = Surreal::new::<RocksDb>(data_dir).await
            .context("open embedded RocksDb")?;
        db.use_ns(NS).use_db(DB).await.context("select ns/db")?;

        let store = Self { db };
        store.migrate().await?;
        Ok(store)
    }

    /// Boot with in-memory engine (ephemeral — for tests / short-lived agents).
    pub async fn open_mem() -> Result<Self> {
        let db = Surreal::new::<Mem>(()).await
            .context("open embedded Mem engine")?;
        db.use_ns(NS).use_db(DB).await.context("select ns/db")?;

        let store = Self { db };
        store.migrate().await?;
        Ok(store)
    }

    /// Apply schema migration (idempotent — DEFINE is safe to re-run).
    async fn migrate(&self) -> Result<()> {
        info!("applying schema migration");
        self.db.query(MIGRATION).await.context("schema migration")?;
        info!("schema ready");
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Memory — write
    // -----------------------------------------------------------------------

    pub async fn create_memory(&self, input: MemoryInput) -> Result<Memory> {
        let scope = input.scope.unwrap_or_default();
        let source_kind = input.source_kind.unwrap_or_default();

        let mut res = self.db
            .query(
                r#"
                CREATE memory SET
                    category         = $category,
                    content          = $content,
                    summary          = $summary,
                    agent_id         = $agent_id,
                    session_id       = $session_id,
                    scope            = $scope,
                    valid_time_start = $valid_time_start,
                    valid_time_end   = $valid_time_end,
                    source_kind      = $source_kind,
                    source_ref       = $source_ref,
                    source_trust     = $source_trust,
                    confidence       = $confidence,
                    importance       = $importance,
                    keywords         = $keywords,
                    tags             = $tags,
                    embedding        = $embedding,
                    superseded       = false,
                    created_at       = time::now(),
                    updated_at       = time::now()
                RETURN *;
                "#,
            )
            .bind(("category",         serde_json::to_value(&input.category)?))
            .bind(("content",          input.content))
            .bind(("summary",          input.summary))
            .bind(("agent_id",         input.agent_id))
            .bind(("session_id",       input.session_id))
            .bind(("scope",            serde_json::to_value(&scope)?))
            .bind(("valid_time_start", input.valid_time_start))
            .bind(("valid_time_end",   input.valid_time_end))
            .bind(("source_kind",      serde_json::to_value(&source_kind)?))
            .bind(("source_ref",       input.source_ref))
            .bind(("source_trust",     input.source_trust.unwrap_or(0.7)))
            .bind(("confidence",       input.confidence.unwrap_or(0.8)))
            .bind(("importance",       input.importance.unwrap_or(0.5)))
            .bind(("keywords",         input.keywords))
            .bind(("tags",             input.tags))
            .bind(("embedding",        input.embedding))
            .await?;

        let memory: Option<Memory> = res.take(0)?;
        memory.context("create_memory returned nothing")
    }

    /// Spectron supersede-not-overwrite.
    /// 1. Mark old as superseded
    /// 2. Create new with derived_from pointing to old
    /// 3. Create `updates` graph edge new → old
    /// All in one transaction.
    pub async fn supersede_memory(&self, input: SupersedeInput) -> Result<(Memory, Memory)> {
        let old_id = RecordId::from_table_key("memory", input.old_memory_id.clone());
        let source_kind = input.source_kind.unwrap_or_default();

        let mut res = self.db
            .query(
                r#"
                BEGIN TRANSACTION;

                UPDATE $old_id SET
                    superseded     = true,
                    superseded_at  = time::now(),
                    valid_time_end = time::now(),
                    updated_at     = time::now();

                LET $old = SELECT * FROM $old_id;

                LET $new = (CREATE memory SET
                    category         = $old[0].category,
                    content          = $content,
                    agent_id         = $old[0].agent_id,
                    session_id       = $old[0].session_id,
                    scope            = $old[0].scope,
                    source_kind      = $source_kind,
                    source_ref       = $source_ref,
                    source_trust     = $old[0].source_trust,
                    confidence       = $confidence,
                    derived_from     = [$old_id],
                    embedding        = $embedding,
                    superseded       = false,
                    known_time       = time::now(),
                    created_at       = time::now(),
                    updated_at       = time::now()
                RETURN *)[0];

                UPDATE $old_id SET superseded_by = $new.id;

                RELATE ($new.id)->mem_edge->($old_id) SET
                    kind       = 'updates',
                    weight     = 1.0,
                    created_at = time::now();

                RETURN { old: $old[0], new: $new };
                COMMIT TRANSACTION;
                "#,
            )
            .bind(("old_id",      old_id))
            .bind(("content",     input.new_content))
            .bind(("source_kind", serde_json::to_value(&source_kind)?))
            .bind(("source_ref",  input.source_ref))
            .bind(("confidence",  input.confidence.unwrap_or(0.8)))
            .bind(("embedding",   input.embedding))
            .await?;

        #[derive(Deserialize)]
        struct Pair { old: Memory, new: Memory }
        let pair: Option<Pair> = res.take(0)?;
        let pair = pair.context("supersede returned nothing")?;
        Ok((pair.old, pair.new))
    }

    /// Soft forget (valid_time_end = now, superseded = true).
    pub async fn forget(&self, memory_id: &str) -> Result<()> {
        let id = RecordId::from_table_key("memory", memory_id);
        self.db
            .query(
                r#"
                UPDATE $id SET
                    superseded     = true,
                    superseded_at  = time::now(),
                    valid_time_end = time::now(),
                    updated_at     = time::now();
                "#,
            )
            .bind(("id", id))
            .await?;
        Ok(())
    }

    /// Hard purge — GDPR / legal only.
    pub async fn purge(&self, memory_id: &str) -> Result<()> {
        let id = RecordId::from_table_key("memory", memory_id);
        self.db.query("DELETE $id;").bind(("id", id)).await?;
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Memory — retrieval (four-tier ladder)
    // -----------------------------------------------------------------------

    /// Tier 1: direct lookup by category / scope — no embedding needed, sub-ms.
    pub async fn direct_lookup(&self, q: &RecallQuery) -> Result<Vec<Memory>> {
        let active = if q.include_superseded { "true" } else { "superseded = false" };

        let mut surql = format!(
            "SELECT * FROM memory WHERE {} AND agent_id = $agent_id",
            active
        );

        if q.categories.is_some() {
            surql.push_str(" AND category IN $categories");
        }
        if q.min_confidence > 0.0 {
            surql.push_str(" AND confidence >= $min_confidence");
        }
        if q.valid_at.is_some() {
            surql.push_str(" AND (valid_time_start IS NONE OR valid_time_start <= $valid_at)");
            surql.push_str(" AND (valid_time_end IS NONE OR valid_time_end >= $valid_at)");
        }
        surql.push_str(" ORDER BY importance DESC LIMIT $limit;");

        let mut query = self.db.query(surql)
            .bind(("agent_id",       q.agent_id.clone()))
            .bind(("limit",          q.top_k as i64))
            .bind(("min_confidence", q.min_confidence));

        if let Some(cats) = &q.categories {
            query = query.bind(("categories",
                cats.iter().map(|c| serde_json::to_value(c).unwrap()).collect::<Vec<_>>()
            ));
        }
        if let Some(va) = q.valid_at {
            query = query.bind(("valid_at", va));
        }

        let mut res = query.await?;
        let memories: Vec<Memory> = res.take(0)?;
        Ok(memories)
    }

    /// Tier 3: BM25 full-text search.
    pub async fn bm25_search(&self, q: &RecallQuery) -> Result<Vec<(Memory, f32)>> {
        let active = if q.include_superseded { "true" } else { "superseded = false" };

        let surql = format!(
            r#"
            SELECT *, search::score(1) AS _score
            FROM memory
            WHERE {} AND agent_id = $agent_id
                AND content @1@ $query
                AND confidence >= $min_confidence
            ORDER BY _score DESC
            LIMIT $limit;
            "#,
            active
        );

        let mut res = self.db.query(surql)
            .bind(("agent_id",       q.agent_id.clone()))
            .bind(("query",          q.query_text.clone()))
            .bind(("min_confidence", q.min_confidence))
            .bind(("limit",          q.top_k as i64))
            .await?;

        #[derive(Deserialize)]
        struct Row {
            #[serde(flatten)]
            memory: Memory,
            _score: f32,
        }

        let rows: Vec<Row> = res.take(0)?;
        Ok(rows.into_iter().map(|r| (r.memory, r._score)).collect())
    }

    /// Tier 3: HNSW vector search (requires embedding).
    pub async fn vector_search(&self, q: &RecallQuery) -> Result<Vec<(Memory, f32)>> {
        let embedding = match &q.query_embedding {
            Some(e) => e.clone(),
            None => return Ok(vec![]),
        };

        let active = if q.include_superseded { "true" } else { "superseded = false" };

        let surql = format!(
            r#"
            SELECT *, vector::similarity::cosine(embedding, $embedding) AS _score
            FROM memory
            WHERE {} AND agent_id = $agent_id
                AND embedding IS NOT NONE
                AND confidence >= $min_confidence
            ORDER BY _score DESC
            LIMIT $limit;
            "#,
            active
        );

        let mut res = self.db.query(surql)
            .bind(("agent_id",       q.agent_id.clone()))
            .bind(("embedding",      embedding))
            .bind(("min_confidence", q.min_confidence))
            .bind(("limit",          q.top_k as i64))
            .await?;

        #[derive(Deserialize)]
        struct Row {
            #[serde(flatten)]
            memory: Memory,
            _score: f32,
        }

        let rows: Vec<Row> = res.take(0)?;
        Ok(rows.into_iter().map(|r| (r.memory, r._score)).collect())
    }

    /// Fetch full Memory records by IDs (after RRF merge).
    pub async fn fetch_by_ids(&self, ids: &[String]) -> Result<Vec<Memory>> {
        if ids.is_empty() { return Ok(vec![]); }

        let record_ids: Vec<RecordId> = ids.iter()
            .map(|id| RecordId::from_table_key("memory", id.as_str()))
            .collect();

        let mut res = self.db
            .query("SELECT * FROM $ids;")
            .bind(("ids", record_ids))
            .await?;

        let memories: Vec<Memory> = res.take(0)?;
        Ok(memories)
    }

    // -----------------------------------------------------------------------
    // Retrieval trace
    // -----------------------------------------------------------------------

    pub async fn write_trace(
        &self,
        q: &RecallQuery,
        result_ids: &[String],
        tier: RetrievalTier,
    ) -> Result<RetrievalTrace> {
        let record_ids: Vec<RecordId> = result_ids.iter()
            .map(|id| RecordId::from_table_key("memory", id.as_str()))
            .collect();

        let mut res = self.db
            .query(
                r#"
                CREATE retrieval_trace SET
                    agent_id        = $agent_id,
                    session_id      = $session_id,
                    query_text      = $query_text,
                    query_embedding = $query_embedding,
                    tier            = $tier,
                    result_ids      = $result_ids,
                    created_at      = time::now()
                RETURN *;
                "#,
            )
            .bind(("agent_id",        q.agent_id.clone()))
            .bind(("session_id",      q.session_id.clone()))
            .bind(("query_text",      q.query_text.clone()))
            .bind(("query_embedding", q.query_embedding.clone()))
            .bind(("tier",            tier as i64))
            .bind(("result_ids",      record_ids))
            .await?;

        let trace: Option<RetrievalTrace> = res.take(0)?;
        trace.context("write_trace returned nothing")
    }

    pub async fn feedback_trace(
        &self,
        trace_id: &str,
        useful: Option<bool>,
        correction: Option<bool>,
    ) -> Result<()> {
        let id = RecordId::from_table_key("retrieval_trace", trace_id);
        self.db
            .query("UPDATE $id SET useful = $useful, correction = $correction;")
            .bind(("id",         id))
            .bind(("useful",     useful))
            .bind(("correction", correction))
            .await?;
        Ok(())
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
        let src = RecordId::from_table_key("memory", source_id);
        let tgt = RecordId::from_table_key("memory", target_id);
        self.db
            .query(
                r#"
                RELATE $src->mem_edge->$tgt
                    SET kind = $kind, weight = $weight, created_at = time::now();
                "#,
            )
            .bind(("src",    src))
            .bind(("tgt",    tgt))
            .bind(("kind",   serde_json::to_value(&kind)?))
            .bind(("weight", weight))
            .await?;
        Ok(())
    }

    pub async fn related_memories(
        &self,
        memory_id: &str,
        kinds: Option<Vec<EdgeKind>>,
    ) -> Result<Vec<Memory>> {
        let id = RecordId::from_table_key("memory", memory_id);

        let surql = if kinds.is_some() {
            "SELECT ->mem_edge[WHERE kind IN $kinds]->memory.* AS related FROM $id;"
        } else {
            "SELECT ->mem_edge->memory.* AS related FROM $id;"
        };

        let mut query = self.db.query(surql).bind(("id", id));

        if let Some(ks) = kinds {
            query = query.bind(("kinds",
                ks.iter().map(|k| serde_json::to_value(k).unwrap()).collect::<Vec<_>>()
            ));
        }

        #[derive(Deserialize)]
        struct Row { related: Vec<Memory> }
        let mut res = query.await?;
        let rows: Vec<Row> = res.take(0)?;
        Ok(rows.into_iter().flat_map(|r| r.related).collect())
    }

    // -----------------------------------------------------------------------
    // Decision trace
    // -----------------------------------------------------------------------

    pub async fn create_decision_trace(&self, dt: &DecisionTrace) -> Result<DecisionTrace> {
        let mut res = self.db
            .query(
                r#"
                CREATE decision_trace SET
                    run_id      = $run_id,
                    step_id     = $step_id,
                    agent_id    = $agent_id,
                    actor       = $actor,
                    action      = $action,
                    input       = $input,
                    output      = $output,
                    status      = $status,
                    memory_refs = $memory_refs,
                    created_at  = time::now()
                RETURN *;
                "#,
            )
            .bind(("run_id",      dt.run_id.clone()))
            .bind(("step_id",     dt.step_id.clone()))
            .bind(("agent_id",    dt.agent_id.clone()))
            .bind(("actor",       dt.actor.clone()))
            .bind(("action",      dt.action.clone()))
            .bind(("input",       dt.input.clone()))
            .bind(("output",      dt.output.clone()))
            .bind(("status",      serde_json::to_value(&dt.status)?))
            .bind(("memory_refs", dt.memory_refs.clone()))
            .await?;

        let trace: Option<DecisionTrace> = res.take(0)?;
        trace.context("create_decision_trace returned nothing")
    }

    // -----------------------------------------------------------------------
    // Working memory (Cortex)
    // -----------------------------------------------------------------------

    pub async fn upsert_working_memory(&self, wm: &WorkingMemory) -> Result<WorkingMemory> {
        let layer_str = serde_json::to_value(&wm.layer)?
            .as_str().unwrap_or("unknown").to_string();
        let wm_id = format!("{}_{}", wm.agent_id, layer_str);
        let id = RecordId::from_table_key("working_memory", wm_id.as_str());

        let mut res = self.db
            .query(
                r#"
                UPSERT $id SET
                    agent_id        = $agent_id,
                    layer           = $layer,
                    content         = $content,
                    source_memories = $source_memories,
                    valid_date      = $valid_date,
                    token_count     = $token_count,
                    updated_at      = time::now()
                RETURN *;
                "#,
            )
            .bind(("id",              id))
            .bind(("agent_id",        wm.agent_id.clone()))
            .bind(("layer",           serde_json::to_value(&wm.layer)?))
            .bind(("content",         wm.content.clone()))
            .bind(("source_memories", wm.source_memories.clone()))
            .bind(("valid_date",      wm.valid_date))
            .bind(("token_count",     wm.token_count))
            .await?;

        let result: Option<WorkingMemory> = res.take(0)?;
        result.context("upsert_working_memory returned nothing")
    }

    pub async fn get_working_memory(
        &self,
        agent_id: &str,
        layers: Option<Vec<WorkingMemoryLayer>>,
    ) -> Result<Vec<WorkingMemory>> {
        let surql = if layers.is_some() {
            "SELECT * FROM working_memory WHERE agent_id = $agent_id AND layer IN $layers;"
        } else {
            "SELECT * FROM working_memory WHERE agent_id = $agent_id;"
        };

        let mut query = self.db.query(surql).bind(("agent_id", agent_id.to_string()));

        if let Some(ls) = layers {
            query = query.bind(("layers",
                ls.iter().map(|l| serde_json::to_value(l).unwrap()).collect::<Vec<_>>()
            ));
        }

        let mut res = query.await?;
        let wms: Vec<WorkingMemory> = res.take(0)?;
        Ok(wms)
    }

    // -----------------------------------------------------------------------
    // Tri-temporal queries
    // -----------------------------------------------------------------------

    /// What did the agent believe to be true at a point in time?
    pub async fn memories_valid_at(
        &self,
        agent_id: &str,
        point_in_time: chrono::DateTime<chrono::Utc>,
        categories: Option<Vec<MemoryCategory>>,
    ) -> Result<Vec<Memory>> {
        let surql = if categories.is_some() {
            r#"
            SELECT * FROM memory
            WHERE agent_id = $agent_id
                AND (valid_time_start IS NONE OR valid_time_start <= $pit)
                AND (valid_time_end IS NONE OR valid_time_end >= $pit)
                AND category IN $categories
            ORDER BY confidence DESC;
            "#
        } else {
            r#"
            SELECT * FROM memory
            WHERE agent_id = $agent_id
                AND (valid_time_start IS NONE OR valid_time_start <= $pit)
                AND (valid_time_end IS NONE OR valid_time_end >= $pit)
            ORDER BY confidence DESC;
            "#
        };

        let mut query = self.db.query(surql)
            .bind(("agent_id", agent_id.to_string()))
            .bind(("pit",      point_in_time));

        if let Some(cats) = categories {
            query = query.bind(("categories",
                cats.iter().map(|c| serde_json::to_value(c).unwrap()).collect::<Vec<_>>()
            ));
        }

        let mut res = query.await?;
        let memories: Vec<Memory> = res.take(0)?;
        Ok(memories)
    }

    /// Walk the supersession chain — history is always queryable.
    pub async fn supersession_lineage(&self, memory_id: &str) -> Result<Vec<Memory>> {
        let id = RecordId::from_table_key("memory", memory_id);
        let mut res = self.db
            .query(
                r#"
                SELECT * FROM memory
                WHERE id = $id
                    OR superseded_by = $id
                    OR derived_from CONTAINS $id
                ORDER BY created_at DESC;
                "#,
            )
            .bind(("id", id))
            .await?;

        let memories: Vec<Memory> = res.take(0)?;
        Ok(memories)
    }

    // -----------------------------------------------------------------------
    // Evolution queue
    // -----------------------------------------------------------------------

    /// Claim a batch of pending evolution jobs atomically.
    pub async fn claim_evolution_jobs(&self, agent_id: &str, limit: usize) -> Result<Vec<EvolutionJob>> {
        let mut res = self.db
            .query(
                r#"
                UPDATE evolution_queue
                SET status = 'processing'
                WHERE agent_id = $agent_id AND status = 'pending'
                LIMIT $limit
                RETURN AFTER;
                "#,
            )
            .bind(("agent_id", agent_id.to_string()))
            .bind(("limit",    limit as i64))
            .await?;

        let jobs: Vec<EvolutionJob> = res.take(0)?;
        Ok(jobs)
    }

    pub async fn complete_evolution_job(&self, job_id: &RecordId) -> Result<()> {
        self.db
            .query("UPDATE $id SET status = 'done', processed_at = time::now();")
            .bind(("id", job_id.clone()))
            .await?;
        Ok(())
    }

    pub async fn skip_evolution_job(&self, job_id: &RecordId) -> Result<()> {
        self.db
            .query("UPDATE $id SET status = 'skipped', processed_at = time::now();")
            .bind(("id", job_id.clone()))
            .await?;
        Ok(())
    }

    // -----------------------------------------------------------------------
    // Raw query (escape hatch)
    // -----------------------------------------------------------------------

    pub async fn query_raw(&self, surql: &str) -> Result<surrealdb::Response> {
        Ok(self.db.query(surql).await?)
    }

    pub async fn select_memory(&self, memory_id: &str) -> Result<Option<Memory>> {
        let id = RecordId::from_table_key("memory", memory_id);
        let memory: Option<Memory> = self.db.select(id).await?;
        Ok(memory)
    }
}

// ---------------------------------------------------------------------------
// Reciprocal Rank Fusion — merge BM25 + vector ranked lists
// ---------------------------------------------------------------------------

pub fn reciprocal_rank_fusion(
    list_a: &[(String, f32)],
    list_b: &[(String, f32)],
    k: usize,
    top_n: usize,
) -> Vec<String> {
    use std::collections::HashMap;

    let mut scores: HashMap<String, f64> = HashMap::new();

    for (rank, (id, _)) in list_a.iter().enumerate() {
        *scores.entry(id.clone()).or_insert(0.0) += 1.0 / (k + rank + 1) as f64;
    }
    for (rank, (id, _)) in list_b.iter().enumerate() {
        *scores.entry(id.clone()).or_insert(0.0) += 1.0 / (k + rank + 1) as f64;
    }

    let mut ranked: Vec<(String, f64)> = scores.into_iter().collect();
    ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    ranked.into_iter().take(top_n).map(|(id, _)| id).collect()
}

// ---------------------------------------------------------------------------
// Needed for serde Deserialize in query results
// ---------------------------------------------------------------------------
use serde::Deserialize;
