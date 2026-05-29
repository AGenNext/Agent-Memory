mod config;
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

    /// Path to config TOML file. Defaults to <data_dir>/config.toml or built-in defaults.
    #[arg(long, env = "AGENT_MEMORY_CONFIG")]
    config: Option<std::path::PathBuf>,

    /// Write default config.toml to stdout and exit.
    #[arg(long)]
    print_default_config: bool,

    /// Server mode.
    ///   mcp  → MCP server on stdio only (default)
    ///   http → SurrealDB HTTP endpoint only (for Python/TS/Go SDKs)
    ///   both → MCP on stdio + SurrealDB HTTP endpoint
    #[arg(long, env = "AGENT_MEMORY_MODE", default_value = "mcp")]
    mode: String,

    /// Port for SurrealDB HTTP endpoint (used with --mode http or both).
    #[arg(long, env = "AGENT_MEMORY_DB_PORT", default_value = "8000")]
    db_port: u16,

    /// Bind address for SurrealDB HTTP endpoint.
    #[arg(long, env = "AGENT_MEMORY_DB_BIND", default_value = "0.0.0.0")]
    db_bind: String,

    /// SurrealDB server username (for HTTP mode).
    #[arg(long, env = "AGENT_MEMORY_DB_USER", default_value = "root")]
    db_user: String,

    /// SurrealDB server password (for HTTP mode).
    #[arg(long, env = "AGENT_MEMORY_DB_PASS", default_value = "root")]
    db_pass: String,

    /// Path to surreal binary (optional — searches PATH by default).
    #[arg(long, env = "SURREAL_BIN")]
    surreal_bin: Option<std::path::PathBuf>,

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

    // Print default config and exit
    if cli.print_default_config {
        let default = config::Config::default();
        let content = toml::to_string_pretty(&default)
            .expect("serialise default config");
        println!("{}", content);
        return Ok(());
    }

    // Handle schema-only command before DB boot
    if let Some(Cmd::Schema) = &cli.command {
        print!("{}", include_str!("../migrations/001_memory.surql"));
        return Ok(());
    }

    // Load config
    let config_path = cli.config.clone().unwrap_or_else(|| {
        cli.data_dir.as_ref()
            .map(|d| d.join("config.toml"))
            .unwrap_or_else(|| std::path::PathBuf::from("config.toml"))
    });
    let cfg = config::Config::load(&config_path)?;
    info!("decay thresholds: retrieval={:.3} escalating={:.3} confidence_floor={:.3}",
        cfg.retrieval_threshold(),
        cfg.escalating_threshold(),
        cfg.confidence_floor(),
    );

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

    let service = MemoryService::new(store, cfg.clone());

    // Dispatch
    match cli.command.unwrap_or(Cmd::Mcp) {
        Cmd::Schema => unreachable!(),

        Cmd::Test => {
            run_self_test(service).await?;
        }

        Cmd::Mcp => {
            // Start SurrealDB HTTP server if mode includes http
            let _surreal_server = if cli.mode == "http" || cli.mode == "both" {
                let bind = format!("{}:{}", cli.db_bind, cli.db_port);
                let srv_cfg = server::SurrealServerConfig {
                    surreal_bin:         cli.surreal_bin.clone(),
                    bind_addr:           bind.clone(),
                    data_dir:            cli.data_dir.clone().unwrap_or_else(|| std::path::PathBuf::from("./data")),
                    ns:                  "agnxxt".to_string(),
                    db:                  "agent_memory".to_string(),
                    user:                cli.db_user.clone(),
                    pass:                cli.db_pass.clone(),
                    allow_guests:        false,
                    health_timeout_secs: 30,
                };
                let srv = server::SurrealServer::start(srv_cfg).await?;
                server::print_connection_info(&bind, "agnxxt", "agent_memory");
                Some(srv)
            } else {
                None
            };

            // If mode is http-only, just keep the server alive
            if cli.mode == "http" {
                info!("running in HTTP-only mode — MCP server not started");
                tokio::signal::ctrl_c().await.ok();
                info!("shutting down");
                return Ok(());
            }

            // Start background workers
            let evo_service = service.clone();
            let evo_agents  = cli.agents.clone();
            tokio::spawn(async move {
                EvolutionWorker::new(
                    evo_service,
                    Duration::from_secs(cfg.cortex.evolution_interval_secs),
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
                    Duration::from_secs(cfg.cortex.intraday_interval_secs),
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

    // 9. Conflict: misinterpretation
    let conflict_result = service.resolve_conflict(
        crate::memory::conflict::ConflictInput {
            agent_id:              "test-agent".to_string(),
            session_id:            None,
            conflict_type:         crate::memory::conflict::ConflictType::Misinterpretation,
            human_statement:       "No, I meant technically precise, not short".to_string(),
            prior_memory_id:       None, // no prior in this test
            correct_interpretation: Some("user wants technically precise responses".to_string()),
        }
    ).await?;
    assert!(!conflict_result.halt_reasoning, "misinterpretation should not halt");
    info!("✓ conflict misinterpretation: {}", conflict_result.agent_response);

    // 10. Conflict: factual contradiction — halt_reasoning must be true
    let fact_conflict = service.resolve_conflict(
        crate::memory::conflict::ConflictInput {
            agent_id:              "test-agent".to_string(),
            session_id:            None,
            conflict_type:         crate::memory::conflict::ConflictType::FactualContradiction,
            human_statement:       "I said the budget was $50,000".to_string(),
            prior_memory_id:       None,
            correct_interpretation: None,
        }
    ).await?;
    assert!(fact_conflict.halt_reasoning, "factual contradiction should halt reasoning");
    info!("✓ conflict factual_contradiction halts: {}", fact_conflict.agent_response);

    // 11. Decision log
    let log = service.conflict_history("test-agent", 10).await?;
    assert!(log.len() >= 2, "should have at least 2 conflict trace entries");
    info!("✓ decision log: {} entries", log.len());

    info!("=== all tests passed ===");
    Ok(())
}
