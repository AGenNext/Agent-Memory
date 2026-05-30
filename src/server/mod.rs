/// SurrealDB HTTP server process manager.
///
/// When --mode http or --mode both is set, Agent-Memory spawns
/// a SurrealDB server process against the same data directory.
/// External clients (TypeScript, Go, etc.) connect to
/// that HTTP endpoint using SurrealDB's official client SDKs.
///
/// The binary manages the server lifecycle:
///   start → health check → serve → graceful shutdown on SIGTERM/SIGINT
///
/// No custom REST API. No custom SDK needed.
/// SurrealDB's own protocol and clients handle everything.

use std::path::{Path, PathBuf};
use std::process::Stdio;
use std::time::Duration;

use anyhow::{bail, Context, Result};
use tokio::process::{Child, Command};
use tokio::time::{sleep, timeout};
use tracing::{error, info, warn};

// ---------------------------------------------------------------------------
// SurrealServer
// ---------------------------------------------------------------------------

pub struct SurrealServer {
    process:   Child,
    bind_addr: String,
}

#[derive(Debug, Clone)]
pub struct SurrealServerConfig {
    /// Path to the surreal binary. If None, searches PATH.
    pub surreal_bin:  Option<PathBuf>,
    /// Bind address. Default: 0.0.0.0:8000
    pub bind_addr:    String,
    /// Data directory (same one used by the embedded engine).
    pub data_dir:     PathBuf,
    /// SurrealDB namespace
    pub ns:           String,
    /// SurrealDB database
    pub db:           String,
    /// Username for the SurrealDB server
    pub user:         String,
    /// Password for the SurrealDB server
    pub pass:         String,
    /// Whether to allow anonymous access (no auth required for reads)
    pub allow_guests: bool,
    /// How long to wait for the server to become healthy
    pub health_timeout_secs: u64,
}

impl Default for SurrealServerConfig {
    fn default() -> Self {
        Self {
            surreal_bin:         None,
            bind_addr:           "0.0.0.0:8000".to_string(),
            data_dir:            PathBuf::from("./data"),
            ns:                  "agnxxt".to_string(),
            db:                  "agent_memory".to_string(),
            user:                "root".to_string(),
            pass:                "root".to_string(),
            allow_guests:        false,
            health_timeout_secs: 30,
        }
    }
}

impl SurrealServer {
    /// Spawn a SurrealDB server process and wait until it is healthy.
    pub async fn start(cfg: SurrealServerConfig) -> Result<Self> {
        let bin = resolve_surreal_bin(cfg.surreal_bin.as_deref())?;

        std::fs::create_dir_all(&cfg.data_dir)
            .with_context(|| format!("create data dir {:?}", cfg.data_dir))?;

        let data_path = format!("rocksdb:{}", cfg.data_dir.display());

        info!(
            "starting SurrealDB server: {} start --bind {} {}",
            bin.display(),
            cfg.bind_addr,
            data_path
        );

        let process = Command::new(&bin)
            .args([
                "start",
                "--bind",         &cfg.bind_addr,
                "--user",         &cfg.user,
                "--pass",         &cfg.pass,
                "--log",          "info",
                &data_path,
            ])
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .kill_on_drop(true)
            .spawn()
            .with_context(|| format!("spawn surreal binary {:?}", bin))?;

        let server = Self {
            process,
            bind_addr: cfg.bind_addr.clone(),
        };

        // Wait until healthy
        let health_url = format!("http://{}/health", cfg.bind_addr);
        server.wait_healthy(&health_url, cfg.health_timeout_secs).await
            .with_context(|| format!("SurrealDB server did not become healthy at {}", cfg.bind_addr))?;

        info!("SurrealDB server ready at http://{}", cfg.bind_addr);
        info!("  SQL endpoint: http://{}/sql", cfg.bind_addr);
        info!("  RPC endpoint: http://{}/rpc", cfg.bind_addr);
        info!("  WS  endpoint: ws://{}/rpc", cfg.bind_addr);
        info!("  Namespace: {} / Database: {}", cfg.ns, cfg.db);
        info!("  Credentials: {}:*****", cfg.user);

        Ok(server)
    }

    async fn wait_healthy(&self, health_url: &str, timeout_secs: u64) -> Result<()> {
        let client = reqwest::Client::new();
        let deadline = Duration::from_secs(timeout_secs);

        let result = timeout(deadline, async {
            loop {
                match client.get(health_url).send().await {
                    Ok(resp) if resp.status().is_success() => {
                        return Ok(());
                    }
                    Ok(resp) => {
                        warn!("health check returned {}", resp.status());
                    }
                    Err(e) => {
                        warn!("health check error: {}", e);
                    }
                }
                sleep(Duration::from_millis(500)).await;
            }
        }).await;

        match result {
            Ok(r) => r,
            Err(_) => bail!("timed out after {}s", timeout_secs),
        }
    }

    /// Gracefully stop the server process.
    pub async fn stop(mut self) {
        info!("stopping SurrealDB server");
        if let Err(e) = self.process.kill().await {
            error!("error stopping SurrealDB server: {}", e);
        }
    }

    pub fn bind_addr(&self) -> &str {
        &self.bind_addr
    }
}

// ---------------------------------------------------------------------------
// Binary resolution
// ---------------------------------------------------------------------------

fn resolve_surreal_bin(override_path: Option<&Path>) -> Result<PathBuf> {
    if let Some(p) = override_path {
        if p.exists() {
            return Ok(p.to_path_buf());
        }
        bail!("surreal binary not found at {:?}", p);
    }

    // Search PATH
    let candidates = ["surreal", "surrealdb"];
    for name in &candidates {
        if let Ok(path) = which_surreal(name) {
            info!("found surreal binary: {:?}", path);
            return Ok(path);
        }
    }

    // Check common install locations
    let common = [
        "/usr/local/bin/surreal",
        "/usr/bin/surreal",
        "~/.cargo/bin/surreal",
    ];
    for path in &common {
        let p = PathBuf::from(path);
        if p.exists() {
            return Ok(p);
        }
    }

    bail!(
        "surreal binary not found in PATH or common locations. \
         Install it with: curl --proto '=https' --tlsv1.2 -sSf https://install.surrealdb.com | sh\n\
         Or set SURREAL_BIN env var / --surreal-bin CLI flag to the binary path."
    )
}

fn which_surreal(name: &str) -> Result<PathBuf> {
    let output = std::process::Command::new("which")
        .arg(name)
        .output()
        .context("run which")?;

    if output.status.success() {
        let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
        Ok(PathBuf::from(path))
    } else {
        bail!("{} not in PATH", name)
    }
}

// ---------------------------------------------------------------------------
// Connection info printed to stdout
// — for frameworks to read and connect automatically
// ---------------------------------------------------------------------------

pub fn print_connection_info(bind_addr: &str, ns: &str, db: &str) {
    println!();
    println!("╔══════════════════════════════════════════════════════════╗");
    println!("║           Agent-Memory — SurrealDB HTTP Endpoint         ║");
    println!("╠══════════════════════════════════════════════════════════╣");
    println!("║  HTTP  http://{:<43}║", bind_addr);
    println!("║  WS    ws://{:<45}║", format!("{}/rpc", bind_addr));
    println!("║  SQL   http://{:<43}║", format!("{}/sql", bind_addr));
    println!("╠══════════════════════════════════════════════════════════╣");
    println!("║  Namespace : {:<44}║", ns);
    println!("║  Database  : {:<44}║", db);
    println!("╠══════════════════════════════════════════════════════════╣");
    println!("║  Node.js   : npm install surrealdb                       ║");
    println!("║  Go        : go get github.com/surrealdb/surrealdb.go    ║");
    println!("╚══════════════════════════════════════════════════════════╝");
    println!();
    println!("  Quick connect (Node.js):");
    println!("    import {{ Surreal }} from 'surrealdb';");
    println!("    const db = new Surreal();");
    println!("    await db.connect('http://{}');", bind_addr);
    println!("    await db.signin({{ username: 'root', password: 'root' }});");
    println!("    await db.use({{ namespace: '{}', database: '{}' }});", ns, db);
    println!();
}
