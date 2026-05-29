mod memory;
mod mcp;
mod services;

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use anyhow::Result;
use clap::{Parser, Subcommand};
use tracing::info;
use tracing_subscriber::{fmt, EnvFilter};

use memory::{service::MemoryService, store::Store};
use mcp::server::serve_stdio;
use services::{cortex::CortexSynthesiser, evolution::EvolutionWorker};

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

#[derive(Parser)]
#[command(name = "agent-memory", version, about = "Agent-Memory: open memory layer for AI agents")]
struct Cli {
    /// Path to RocksDB data directory. Omit for in-memory (ephemeral).
    #[arg(long, env = "AGENT_MEMORY_DATA_DIR")]
    data_dir: Option<PathBuf>,

    /// Agent IDs to manage (comma-separated). Used by background workers.
    #[arg(long, env = "AGENT_MEMORY_AGENTS", value_delimiter = ',', default_value = "default")]
    agents: Vec<String>,

    /// Evolution worker interval in seconds.
    #[arg(long, env = "AGENT_MEMORY_EVOLUTION_INTERVAL", default_value = "30")]
    evolution_interval: u64,

    /// Cortex synthesis interval in seconds.
    #[arg(long, env = "AGENT_MEMORY_CORTEX_INTERVAL", default_value = "3600")]
    cortex_interval: u64,

    /// Log level (trace, debug, info, warn, error).
    #[arg(long, env = "RUST_LOG", default_value = "info")]
    log_level: String,

    #[command(subcommand)]
    command: Option<Cmd>,
}

#[derive(Subcommand)]
enum Cmd {
    /// Run as MCP server on stdio (default — for Claude Desktop / Claude Code).
    Mcp,
    /// Print schema SQL and exit.
    Schema,
    /// Run a quick self-test against the embedded DB.
    Test,
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Tracing
    fmt()
        .with_env_filter(EnvFilter::new(&cli.log_level))
        .with_target(false)
        .init();

    info!("agent-memory v{}", env!("CARGO_PKG_VERSION"));

    // Handle schema-only command before DB boot
    if let Some(Cmd::Schema) = &cli.command {
        print!("{}", include_str!("../migrations/001_memory.surql"));
        return Ok(());
    }

    // Boot embedded store
    let store = match cli.data_dir {
        Some(ref dir) => {
            info!("opening RocksDB at {:?}", dir);
            Store::open(dir.clone()).await?
        }
        None => {
            info!("opening in-memory store (ephemeral)");
            Store::open_mem().await?
        }
    };

    let service = MemoryService::new(store);

    // Dispatch
    match cli.command.unwrap_or(Cmd::Mcp) {
        Cmd::Schema => unreachable!(),

        Cmd::Test => {
            run_self_test(service).await?;
        }

        Cmd::Mcp => {
            // Start background workers
            let evo_service = service.clone();
            let evo_agents  = cli.agents.clone();
            tokio::spawn(async move {
                EvolutionWorker::new(
                    evo_service,
                    Duration::from_secs(cli.evolution_interval),
                    20,
                    evo_agents,
                ).run().await;
            });

            let cortex_service = service.clone();
            let cortex_agents  = cli.agents.clone();
            let cortex_fn = default_synthesise_fn();
            tokio::spawn(async move {
                CortexSynthesiser::new(
                    cortex_service,
                    Duration::from_secs(cli.cortex_interval),
                    cortex_agents,
                    cortex_fn,
                ).run().await;
            });

            // Serve MCP on stdio — blocks until stdin closes
            serve_stdio(service).await?;
        }
    }

    Ok(())
}

// ---------------------------------------------------------------------------
// Default synthesis function — simple concatenation / truncation.
// In production replace with an LLM call via environment-configured endpoint.
// ---------------------------------------------------------------------------

fn default_synthesise_fn() -> services::cortex::SynthesiseFn {
    Arc::new(|layer, source_text, _agent_id| {
        Box::pin(async move {
            // Simple implementation: truncate to 500 words.
            // Replace with LLM call: POST to $SYNTHESIS_ENDPOINT.
            let words: Vec<&str> = source_text.split_whitespace().collect();
            let summary = if words.len() > 500 {
                format!("[truncated to 500 words] {}", words[..500].join(" "))
            } else if source_text.is_empty() {
                format!("[{:?}] no content yet", layer)
            } else {
                source_text
            };
            Ok(summary)
        })
    })
}

// ---------------------------------------------------------------------------
// Self-test — verifies embedded DB + schema + core operations
// ---------------------------------------------------------------------------

async fn run_self_test(service: MemoryService) -> Result<()> {
    use memory::types::*;

    info!("=== agent-memory self-test ===");

    // 1. Create a memory
    let mem = service.remember(MemoryInput {
        agent_id:   "test-agent".to_string(),
        content:    "The user prefers concise responses with code examples.".to_string(),
        category:   MemoryCategory::Identity,
        importance: Some(0.9),
        confidence: Some(0.95),
        keywords:   Some(vec!["preferences".to_string(), "communication".to_string()]),
        tags:       Some(vec!["identity".to_string()]),
        summary:    None,
        session_id: None,
        scope:      None,
        valid_time_start: None,
        valid_time_end:   None,
        source_kind: None,
        source_ref:  None,
        source_trust: None,
        derived_from: None,
        embedding:   None,
    }).await?;

    let mem_id = mem.id.as_ref()
        .map(|id| id.key().to_string())
        .unwrap_or_default();

    info!("✓ created memory {}", mem_id);

    // 2. Recall it
    let result = service.recall(RecallQuery {
        agent_id:   "test-agent".to_string(),
        query_text: "user preferences".to_string(),
        top_k:      5,
        tier:       RetrievalTier::DirectLookup,
        ..Default::default()
    }).await?;

    assert!(!result.memories.is_empty(), "recall returned nothing");
    info!("✓ recall: {} memories, tier={:?}", result.memories.len(), result.tier_used);

    // 3. Supersede it
    let (_old, new) = service.update(SupersedeInput {
        old_memory_id: mem_id.clone(),
        new_content:   "The user prefers bullet-point responses with Python examples.".to_string(),
        confidence:    Some(0.95),
        source_kind:   None,
        source_ref:    None,
        embedding:     None,
    }).await?;

    let new_id = new.id.as_ref().map(|id| id.key().to_string()).unwrap_or_default();
    info!("✓ superseded {} → {}", mem_id, new_id);

    // 4. Verify old is superseded
    let old_fetched = service.store.select_memory(&mem_id).await?;
    assert!(old_fetched.map(|m| m.superseded).unwrap_or(false), "old memory should be superseded");
    info!("✓ supersession verified");

    // 5. Supersession lineage
    let lineage = service.history(&mem_id).await?;
    assert!(lineage.len() >= 2, "lineage should contain at least 2 records");
    info!("✓ lineage: {} records", lineage.len());

    // 6. Soft forget
    service.forget(&new_id).await?;
    let forgotten = service.store.select_memory(&new_id).await?;
    assert!(forgotten.map(|m| m.superseded).unwrap_or(false), "forgotten memory should be superseded");
    info!("✓ forget verified");

    // 7. Working memory upsert
    service.upsert_working_memory(memory::types::WorkingMemory {
        id:              None,
        agent_id:        "test-agent".to_string(),
        layer:           WorkingMemoryLayer::IdentityContext,
        content:         "Test agent — prefers concise code examples.".to_string(),
        source_memories: None,
        valid_date:      None,
        token_count:     Some(8),
        created_at:      None,
        updated_at:      None,
    }).await?;
    info!("✓ working memory upsert");

    // 8. Cortex context
    let ctx = service.context("test-agent").await?;
    assert!(!ctx.is_empty(), "context should have at least 1 layer");
    info!("✓ cortex context: {} layers", ctx.len());

    info!("=== all tests passed ===");
    Ok(())
}
