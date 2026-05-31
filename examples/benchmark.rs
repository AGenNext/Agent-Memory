//! Memory benchmark harness.
//!
//! Drives the public `agent_memory` API against the fixtures in
//! `benchmarks/memory/fixtures/` and reports **measured** numbers: recall
//! accuracy and ingest/recall latency. Nothing here is hard-coded — every
//! number printed is produced by this run.
//!
//! ## Run it
//!
//! ```sh
//! cargo run --release --example benchmark
//! # write a markdown report instead of just stdout:
//! cargo run --release --example benchmark -- --out benchmarks/results/agent-memory.md
//! ```
//!
//! ## Comparing against other frameworks
//!
//! This harness measures **agent-memory** directly because it is the only
//! framework available in-process. Competing frameworks (Mem0, Zep, Letta,
//! LangChain memory) run as external services and require their own API keys
//! and network access, so they are *not* measured here and we deliberately
//! emit no numbers for them. To add one, implement the `MemoryFramework`
//! trait against its client and add it to `frameworks()` — see
//! `benchmarks/README.md` for the contract and the apples-to-apples rules.

use std::path::PathBuf;
use std::time::Instant;

use agent_memory::{AgentMemory, MemoryCategory, MemoryInput, RecallQuery, SourceKind};
use anyhow::{Context, Result};
use serde::Deserialize;

// ---------------------------------------------------------------------------
// Fixture types
// ---------------------------------------------------------------------------

#[derive(Debug, Deserialize)]
struct Conversation {
    fixture_id: String,
    #[allow(dead_code)]
    domain: String,
    turns: Vec<Turn>,
}

#[derive(Debug, Deserialize)]
struct Turn {
    #[allow(dead_code)]
    turn: u32,
    speaker: String,
    text: String,
}

#[derive(Debug, Deserialize)]
struct QuerySet {
    query_set: String,
    queries: Vec<Query>,
}

#[derive(Debug, Deserialize)]
struct Query {
    id: String,
    agent_id: String,
    text: String,
    gold: String,
    #[serde(default)]
    gold_alts: Vec<String>,
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

struct Latencies(Vec<u128>); // microseconds

impl Latencies {
    fn mean_ms(&self) -> f64 {
        if self.0.is_empty() {
            return 0.0;
        }
        self.0.iter().sum::<u128>() as f64 / self.0.len() as f64 / 1000.0
    }
    fn p95_ms(&self) -> f64 {
        if self.0.is_empty() {
            return 0.0;
        }
        let mut v = self.0.clone();
        v.sort_unstable();
        let idx = ((v.len() as f64 * 0.95).ceil() as usize).saturating_sub(1);
        v[idx.min(v.len() - 1)] as f64 / 1000.0
    }
}

struct Report {
    framework: String,
    memories_ingested: usize,
    queries_run: usize,
    correct: usize,
    ingest: Latencies,
    recall: Latencies,
}

impl Report {
    fn recall_at_k(&self) -> f64 {
        if self.queries_run == 0 {
            0.0
        } else {
            self.correct as f64 / self.queries_run as f64
        }
    }
}

// ---------------------------------------------------------------------------
// Framework adapter contract
// ---------------------------------------------------------------------------

/// The contract every framework adapter must satisfy so the comparison is
/// apples-to-apples. Implemented for agent-memory below; see
/// `benchmarks/README.md` for how to add Mem0/Zep/Letta/LangChain.
trait MemoryFramework {
    fn name(&self) -> &str;
    /// Store one memory. `speaker` is "user" or "agent".
    fn remember(&self, agent_id: &str, speaker: &str, text: &str) -> Result<()>;
    /// Retrieve up to `top_k` memories for a query; return their text contents.
    fn recall(&self, agent_id: &str, query: &str, top_k: usize) -> Result<Vec<String>>;
}

// ---------------------------------------------------------------------------
// agent-memory adapter
// ---------------------------------------------------------------------------

struct AgentMemoryAdapter {
    rt: tokio::runtime::Handle,
    mem: AgentMemory,
}

impl MemoryFramework for AgentMemoryAdapter {
    fn name(&self) -> &str {
        "agent-memory"
    }

    fn remember(&self, agent_id: &str, speaker: &str, text: &str) -> Result<()> {
        let category = if speaker == "user" {
            MemoryCategory::Identity
        } else {
            MemoryCategory::Episodic
        };
        let source_kind = if speaker == "user" {
            SourceKind::UserTurn
        } else {
            SourceKind::AgentTurn
        };
        let input = MemoryInput {
            agent_id: agent_id.to_string(),
            content: text.to_string(),
            category,
            source_kind: Some(source_kind),
            importance: Some(0.8),
            ..Default::default()
        };
        tokio::task::block_in_place(|| self.rt.block_on(self.mem.remember(input)))?;
        Ok(())
    }

    fn recall(&self, agent_id: &str, query: &str, top_k: usize) -> Result<Vec<String>> {
        let q = RecallQuery {
            agent_id: agent_id.to_string(),
            query_text: query.to_string(),
            top_k,
            ..Default::default()
        };
        let result = tokio::task::block_in_place(|| self.rt.block_on(self.mem.recall(q)))?;
        Ok(result.memories.into_iter().map(|m| m.content).collect())
    }
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

fn is_hit(contents: &[String], query: &Query) -> bool {
    let needles: Vec<String> = std::iter::once(query.gold.clone())
        .chain(query.gold_alts.iter().cloned())
        .map(|s| s.to_lowercase())
        .collect();
    contents
        .iter()
        .any(|c| {
            let lc = c.to_lowercase();
            needles.iter().any(|n| lc.contains(n))
        })
}

// ---------------------------------------------------------------------------
// Harness
// ---------------------------------------------------------------------------

fn fixtures_dir() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("benchmarks/memory/fixtures")
}

fn load_conversations() -> Result<Vec<Conversation>> {
    let dir = fixtures_dir().join("conversations");
    let mut out = Vec::new();
    for entry in std::fs::read_dir(&dir)
        .with_context(|| format!("reading {}", dir.display()))?
    {
        let path = entry?.path();
        if path.extension().and_then(|e| e.to_str()) != Some("json") {
            continue;
        }
        let raw = std::fs::read_to_string(&path)
            .with_context(|| format!("reading {}", path.display()))?;
        let conv: Conversation = serde_json::from_str(&raw)
            .with_context(|| format!("parsing {}", path.display()))?;
        out.push(conv);
    }
    out.sort_by(|a, b| a.fixture_id.cmp(&b.fixture_id));
    Ok(out)
}

fn load_query_set(name: &str) -> Result<QuerySet> {
    let path = fixtures_dir().join("queries").join(name);
    let raw = std::fs::read_to_string(&path)
        .with_context(|| format!("reading {}", path.display()))?;
    serde_json::from_str(&raw).with_context(|| format!("parsing {}", path.display()))
}

fn run(fw: &dyn MemoryFramework, convs: &[Conversation], qs: &QuerySet) -> Result<Report> {
    // Ingest every turn of every conversation under the benchmark agent id.
    // Queries all target "test-agent", so ingest under that id.
    let agent_id = qs
        .queries
        .first()
        .map(|q| q.agent_id.clone())
        .unwrap_or_else(|| "test-agent".to_string());

    let mut ingest = Vec::new();
    let mut ingested = 0usize;
    for conv in convs {
        for turn in &conv.turns {
            let t = Instant::now();
            fw.remember(&agent_id, &turn.speaker, &turn.text)?;
            ingest.push(t.elapsed().as_micros());
            ingested += 1;
        }
    }

    let mut recall = Vec::new();
    let mut correct = 0usize;
    for q in &qs.queries {
        let t = Instant::now();
        let contents = fw.recall(&q.agent_id, &q.text, 10)?;
        recall.push(t.elapsed().as_micros());
        if is_hit(&contents, q) {
            correct += 1;
        } else {
            eprintln!("  miss: {} — {:?}", q.id, q.text);
        }
    }

    Ok(Report {
        framework: fw.name().to_string(),
        memories_ingested: ingested,
        queries_run: qs.queries.len(),
        correct,
        ingest: Latencies(ingest),
        recall: Latencies(recall),
    })
}

fn markdown_table(reports: &[Report], not_run: &[&str], query_set: &str) -> String {
    let mut s = String::new();
    s.push_str(&format!(
        "## Memory benchmark — query set `{query_set}`\n\n\
         Generated by `cargo run --release --example benchmark`. \
         Numbers below are measured on this run; environment varies, so treat \
         absolute latency as machine-relative.\n\n"
    ));
    s.push_str("| Framework | Memories ingested | Queries | Recall@10 | Ingest mean (ms) | Ingest p95 (ms) | Recall mean (ms) | Recall p95 (ms) |\n");
    s.push_str("|---|---:|---:|---:|---:|---:|---:|---:|\n");
    for r in reports {
        s.push_str(&format!(
            "| {} | {} | {} | {:.1}% | {:.3} | {:.3} | {:.3} | {:.3} |\n",
            r.framework,
            r.memories_ingested,
            r.queries_run,
            r.recall_at_k() * 100.0,
            r.ingest.mean_ms(),
            r.ingest.p95_ms(),
            r.recall.mean_ms(),
            r.recall.p95_ms(),
        ));
    }
    for name in not_run {
        s.push_str(&format!(
            "| {name} | — | — | — | — | — | — | — |\n"
        ));
    }
    if !not_run.is_empty() {
        s.push_str(
            "\n> Rows marked `—` have no adapter implemented in this harness yet, so \
             no numbers are reported for them. Implement `MemoryFramework` for each \
             (see `benchmarks/README.md`) and re-run to populate.\n",
        );
    }
    s
}

#[tokio::main(flavor = "multi_thread")]
async fn main() -> Result<()> {
    // crude arg parse: --out <path>
    let mut out_path: Option<PathBuf> = None;
    let mut args = std::env::args().skip(1);
    while let Some(a) = args.next() {
        if a == "--out" {
            out_path = args.next().map(PathBuf::from);
        }
    }

    let convs = load_conversations()?;
    let qs = load_query_set("identity-recall.json")?;
    eprintln!(
        "Loaded {} conversations, query set '{}' with {} queries.\n",
        convs.len(),
        qs.query_set,
        qs.queries.len()
    );

    // agent-memory adapter, backed by an ephemeral in-memory store.
    let mem = AgentMemory::open_mem().await?;
    let adapter = AgentMemoryAdapter {
        rt: tokio::runtime::Handle::current(),
        mem,
    };

    let report = run(&adapter, &convs, &qs)?;

    // Frameworks with no adapter yet — reported as "not run", never faked.
    let not_run = ["mem0", "zep", "letta", "langchain-memory"];

    let table = markdown_table(&[report], &not_run, &qs.query_set);
    println!("\n{table}");

    if let Some(path) = out_path {
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(&path, &table)?;
        eprintln!("Wrote report to {}", path.display());
    }

    Ok(())
}
