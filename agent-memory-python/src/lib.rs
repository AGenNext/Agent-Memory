use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use std::sync::Arc;
use tokio::sync::Mutex;

use agent_memory::{
    AgentMemory as CoreMemory,
    MemoryInput,
    MemoryCategory,
    EpistemicStatus,
    RecallQuery,
    RetrievalTier,
    SupersedeInput,
    ConflictInput,
    ConflictType,
    RecordIdExt,
};

// ---------------------------------------------------------------------------
// AgentMemory Python class
// ---------------------------------------------------------------------------

#[pyclass]
pub struct AgentMemory {
    inner: Arc<Mutex<CoreMemory>>,
    rt:    tokio::runtime::Runtime,
}

#[pymethods]
impl AgentMemory {
    /// Open persistent memory at data_dir.
    #[staticmethod]
    pub fn open(data_dir: &str) -> PyResult<Self> {
        let rt = tokio::runtime::Runtime::new()
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let core = rt.block_on(CoreMemory::open(data_dir))
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(Self { inner: Arc::new(Mutex::new(core)), rt })
    }

    /// Open ephemeral in-memory store. For testing.
    #[staticmethod]
    pub fn open_mem() -> PyResult<Self> {
        let rt = tokio::runtime::Runtime::new()
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        let core = rt.block_on(CoreMemory::open_mem())
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        Ok(Self { inner: Arc::new(Mutex::new(core)), rt })
    }

    /// Store a new memory.
    /// category: 'episodic'|'identity'|'knowledge'|'context'|'instruction'|'uncertainty'
    pub fn remember(
        &self,
        agent_id:         String,
        content:          String,
        category:         String,
        importance:       Option<f64>,
        confidence:       Option<f64>,
        session_id:       Option<String>,
        epistemic_status: Option<String>,
        keywords:         Option<Vec<String>>,
    ) -> PyResult<PyObject> {
        let input = MemoryInput {
            agent_id,
            content,
            category:         parse_category(&category),
            importance,
            confidence,
            session_id,
            epistemic_status: epistemic_status.as_deref().map(parse_epistemic),
            keywords,
            ..Default::default()
        };
        let inner = self.inner.clone();
        let memory = self.rt.block_on(async move {
            inner.lock().await.remember(input).await
        }).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);
            dict.set_item("id", memory.id.map(|id| id.key_str()))?;
            dict.set_item("category", format!("{:?}", memory.category).to_lowercase())?;
            dict.set_item("content", memory.content)?;
            dict.set_item("agent_id", memory.agent_id)?;
            dict.set_item("confidence", memory.confidence)?;
            dict.set_item("importance", memory.importance)?;
            dict.set_item("epistemic_status", format!("{:?}", memory.epistemic_status).to_lowercase())?;
            dict.set_item("superseded", memory.superseded)?;
            Ok(dict.into())
        })
    }

    /// Retrieve memories using hybrid search.
    pub fn recall(
        &self,
        agent_id:       String,
        query_text:     String,
        top_k:          Option<usize>,
        min_confidence: Option<f64>,
        session_id:     Option<String>,
    ) -> PyResult<PyObject> {
        let query = RecallQuery {
            agent_id,
            query_text,
            top_k:          top_k.unwrap_or(10),
            min_confidence:  min_confidence.unwrap_or(0.0),
            session_id,
            tier:            RetrievalTier::Hybrid,
            ..Default::default()
        };
        let inner = self.inner.clone();
        let result = self.rt.block_on(async move {
            inner.lock().await.recall(query).await
        }).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Python::with_gil(|py| {
            let memories = pyo3::types::PyList::empty(py);
            for m in result.memories {
                let d = pyo3::types::PyDict::new(py);
                d.set_item("id", m.id.map(|id| id.key_str()))?;
                d.set_item("content", m.content)?;
                d.set_item("category", format!("{:?}", m.category).to_lowercase())?;
                d.set_item("confidence", m.confidence)?;
                d.set_item("importance", m.importance)?;
                memories.append(d)?;
            }
            let out = pyo3::types::PyDict::new(py);
            out.set_item("memories", memories)?;
            out.set_item("tier_used", result.tier_used as i32)?;
            out.set_item("candidates", result.candidates)?;
            Ok(out.into())
        })
    }

    /// Recall with full escalation — gap protocol if nothing found.
    pub fn recall_or_gap(
        &self,
        agent_id:         String,
        query_text:       String,
        human_insistence: Option<String>,
        top_k:            Option<usize>,
    ) -> PyResult<PyObject> {
        let query = RecallQuery {
            agent_id,
            query_text,
            top_k: top_k.unwrap_or(10),
            tier:  RetrievalTier::Hybrid,
            ..Default::default()
        };
        let inner = self.inner.clone();
        let result = self.rt.block_on(async move {
            inner.lock().await.recall_or_gap(query, human_insistence).await
        }).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Python::with_gil(|py| {
            let out = pyo3::types::PyDict::new(py);
            match result {
                agent_memory::RecallOutcome::Found(r) => {
                    out.set_item("outcome", "found")?;
                    let memories = pyo3::types::PyList::empty(py);
                    for m in r.memories {
                        let d = pyo3::types::PyDict::new(py);
                        d.set_item("content", m.content)?;
                        d.set_item("confidence", m.confidence)?;
                        memories.append(d)?;
                    }
                    out.set_item("memories", memories)?;
                },
                agent_memory::RecallOutcome::Gap(g) => {
                    out.set_item("outcome", "gap")?;
                    out.set_item("suggested_prompt", g.suggested_prompt)?;
                    out.set_item("gap_probe_id", g.id.map(|id| id.key_str()))?;
                }
            }
            Ok(out.into())
        })
    }

    /// Soft-forget a memory.
    pub fn forget(&self, memory_id: String) -> PyResult<()> {
        let inner = self.inner.clone();
        self.rt.block_on(async move {
            inner.lock().await.forget(&memory_id).await
        }).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    /// Reinforce memories — resets Ebbinghaus decay.
    pub fn reinforce(&self, memory_ids: Vec<String>) -> PyResult<()> {
        let inner = self.inner.clone();
        self.rt.block_on(async move {
            inner.lock().await.reinforce(&memory_ids).await
        }).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    /// Get working memory context for prompt injection.
    pub fn context(&self, agent_id: String) -> PyResult<PyObject> {
        let inner = self.inner.clone();
        let layers = self.rt.block_on(async move {
            inner.lock().await.context(&agent_id).await
        }).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;

        Python::with_gil(|py| {
            let out = pyo3::types::PyList::empty(py);
            for layer in layers {
                let d = pyo3::types::PyDict::new(py);
                d.set_item("layer", format!("{:?}", layer.layer).to_lowercase())?;
                d.set_item("content", layer.content)?;
                out.append(d)?;
            }
            Ok(out.into())
        })
    }

    /// Run an analytics query.
    pub fn analytics(
        &self,
        agent_id:    String,
        query:       String,
        window_days: Option<i64>,
    ) -> PyResult<String> {
        let inner = self.inner.clone();
        let result = self.rt.block_on(async move {
            inner.lock().await.analytics(&agent_id, &query, window_days.unwrap_or(30)).await
        }).map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
        serde_json::to_string(&result)
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }

    /// End session — clears active episode.
    pub fn end_session(&self, agent_id: String) -> PyResult<()> {
        let inner = self.inner.clone();
        self.rt.block_on(async move {
            inner.lock().await.end_session(&agent_id).await
        }).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

// ---------------------------------------------------------------------------
// Module registration
// ---------------------------------------------------------------------------

#[pymodule]
fn agent_memory(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<AgentMemory>()?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn parse_category(s: &str) -> MemoryCategory {
    match s {
        "episodic"    => MemoryCategory::Episodic,
        "identity"    => MemoryCategory::Identity,
        "knowledge"   => MemoryCategory::Knowledge,
        "context"     => MemoryCategory::Context,
        "instruction" => MemoryCategory::Instruction,
        "uncertainty" => MemoryCategory::Uncertainty,
        _             => MemoryCategory::Knowledge,
    }
}

fn parse_epistemic(s: &str) -> EpistemicStatus {
    match s {
        "fact"       => EpistemicStatus::Fact,
        "belief"     => EpistemicStatus::Belief,
        "assumption" => EpistemicStatus::Assumption,
        "hearsay"    => EpistemicStatus::Hearsay,
        "inferred"   => EpistemicStatus::Inferred,
        _            => EpistemicStatus::Belief,
    }
}
