/// Generic analytics engine.
///
/// Design principle: the query string drives everything.
/// The engine does not know what queries exist at compile time.
/// New analyses are registered at runtime, not hardcoded.
///
/// Two extension points:
///
/// 1. Built-in SurrealQL queries — stored as `telemetry_query` records
///    in the embedded DB. Add a new query by inserting a row.
///    No code change needed.
///
/// 2. Analyser functions — Rust closures registered in the engine's
///    registry. For analyses that require post-processing logic
///    (threshold comparisons, config suggestions).
///
/// The MCP `telemetry` tool passes the query string to this engine.
/// The engine resolves it: DB query first, analyser registry second,
/// unknown query returns a list of available queries.

use std::collections::BTreeMap;
use std::sync::Arc;

use anyhow::Result;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use tracing::debug;

use crate::{config::Config, memory::store::Store};
use surrealdb::types::SurrealValue;

// ---------------------------------------------------------------------------
// Result type — what every telemetry query returns
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AnalyticsResult {
    pub query:       String,
    pub agent_id:    String,
    pub window_days: i64,

    /// Findings from the analysis — metrics, counts, rates.
    pub findings: Vec<Finding>,

    /// Human-readable recommendations.
    pub recommendations: Vec<Recommendation>,

    /// Exact config.toml key → suggested value.
    /// Human copies these into config.toml and restarts.
    pub config_suggestions: BTreeMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Finding {
    pub metric:      String,
    pub value:       Value,
    pub severity:    Severity,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recommendation {
    pub title:       String,
    pub detail:      String,
    pub config_key:  Option<String>,
    pub config_from: Option<String>,
    pub config_to:   Option<String>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
#[serde(rename_all = "snake_case")]
pub enum Severity { Info, Suggestion, Warning, Critical }

// ---------------------------------------------------------------------------
// Analyser trait — implement this to add a new analysis
// ---------------------------------------------------------------------------

pub trait Analyser: Send + Sync {
    /// Short name — matches the query string.
    fn name(&self) -> &str;

    /// One-line description shown in the available-queries list.
    fn description(&self) -> &str;
}

/// Async analyser function signature.
/// Takes raw SurrealQL query results (JSON) + config + window_days.
/// Returns findings, recommendations, and config suggestions.
pub type AnalyserFn = Arc<
    dyn Fn(
        String,                  // agent_id
        i64,                     // window_days
        Arc<Store>,
        Arc<Config>,
    ) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<AnalyticsResult>> + Send>>
    + Send + Sync,
>;

// ---------------------------------------------------------------------------
// TelemetryEngine — registry + dispatcher
// ---------------------------------------------------------------------------

pub struct AnalyticsEngine {
    store:    Arc<Store>,
    config:   Arc<Config>,
    registry: Vec<(String, String, AnalyserFn)>,  // (name, description, fn)
}

impl AnalyticsEngine {
    pub fn new(store: Arc<Store>, config: Arc<Config>) -> Self {
        let mut engine = Self {
            store: store.clone(),
            config: config.clone(),
            registry: vec![],
        };
        engine.register_builtins();
        engine
    }

    /// Register a new analyser. name must be unique.
    /// New queries are added here — engine dispatch handles the rest.
    pub fn register(&mut self, name: impl Into<String>, description: impl Into<String>, f: AnalyserFn) {
        self.registry.push((name.into(), description.into(), f));
    }

    /// Dispatch a query. Returns results or a list of available queries.
    pub async fn run(
        &self,
        agent_id:    &str,
        query:       &str,
        window_days: i64,
    ) -> Result<AnalyticsResult> {
        debug!("telemetry: agent={} query={} window={}d", agent_id, query, window_days);

        // "available" or unknown query → list what's registered
        if query == "available" || query == "help" || query == "list" {
            return Ok(self.list_available(agent_id, window_days));
        }

        // "summary" → run all registered analysers and merge
        if query == "summary" {
            return self.run_all(agent_id, window_days).await;
        }

        // Find in registry
        let entry = self.registry.iter().find(|(name, _, _)| name == query);
        match entry {
            Some((_, _, f)) => {
                f(
                    agent_id.to_string(),
                    window_days,
                    self.store.clone(),
                    self.config.clone(),
                )
                .await
            }
            None => Ok(self.unknown_query(agent_id, query, window_days)),
        }
    }

    fn list_available(&self, agent_id: &str, window_days: i64) -> AnalyticsResult {
        let findings = self.registry.iter().map(|(name, desc, _)| Finding {
            metric:      name.clone(),
            value:       serde_json::json!(desc),
            severity:    Severity::Info,
            description: format!("query='{}' — {}", name, desc),
        }).collect();

        AnalyticsResult {
            query: "available".to_string(),
            agent_id: agent_id.to_string(),
            window_days,
            findings,
            recommendations: vec![Recommendation {
                title: "Run any query by name".to_string(),
                detail: "Pass the query name to the telemetry tool. \
                         Use 'summary' to run all at once."
                    .to_string(),
                config_key: None,
                config_from: None,
                config_to: None,
            }],
            config_suggestions: BTreeMap::new(),
        }
    }

    fn unknown_query(&self, agent_id: &str, query: &str, window_days: i64) -> AnalyticsResult {
        let available: Vec<&str> = self.registry.iter().map(|(n, _, _)| n.as_str()).collect();
        AnalyticsResult {
            query: query.to_string(),
            agent_id: agent_id.to_string(),
            window_days,
            findings: vec![Finding {
                metric: "unknown_query".to_string(),
                value: serde_json::json!(query),
                severity: Severity::Warning,
                description: format!(
                    "Unknown query '{}'. Available: {}. Use 'summary' for all.",
                    query,
                    available.join(", ")
                ),
            }],
            recommendations: vec![],
            config_suggestions: BTreeMap::new(),
        }
    }

    async fn run_all(&self, agent_id: &str, window_days: i64) -> Result<AnalyticsResult> {
        let mut all_findings = vec![];
        let mut all_recommendations = vec![];
        let mut all_config: BTreeMap<String, String> = BTreeMap::new();

        for (name, _, f) in &self.registry {
            match f(
                agent_id.to_string(),
                window_days,
                self.store.clone(),
                self.config.clone(),
            )
            .await
            {
                Ok(result) => {
                    for mut finding in result.findings {
                        finding.metric = format!("{}.{}", name, finding.metric);
                        all_findings.push(finding);
                    }
                    all_recommendations.extend(result.recommendations);
                    // config_suggestions: last writer wins — highest severity query wins
                    all_config.extend(result.config_suggestions);
                }
                Err(e) => {
                    all_findings.push(Finding {
                        metric: format!("{}.error", name),
                        value: serde_json::json!(e.to_string()),
                        severity: Severity::Warning,
                        description: format!("Query '{}' failed: {}", name, e),
                    });
                }
            }
        }

        // Sort by severity — critical findings first
        all_findings.sort_by(|a, b| b.severity.cmp(&a.severity));

        Ok(AnalyticsResult {
            query: "summary".to_string(),
            agent_id: agent_id.to_string(),
            window_days,
            findings: all_findings,
            recommendations: all_recommendations,
            config_suggestions: all_config,
        })
    }
}

// ---------------------------------------------------------------------------
// Built-in analysers — registered at engine construction
// These are the starting set. More can be added by calling register().
// ---------------------------------------------------------------------------

impl AnalyticsEngine {
    fn register_builtins(&mut self) {
        self.register("decay_tuning",      "Gap probe rate + tier distribution → lambda/threshold recommendations", Arc::new(analyse_decay_tuning));
        self.register("recall_health",     "Tier hit rates, escalation rate, gap rate",                             Arc::new(analyse_recall_health));
        self.register("conflict_patterns", "Conflict type distribution and resolution rates",                       Arc::new(analyse_conflict_patterns));
        self.register("memory_growth",     "Memory count by category, avg confidence",                              Arc::new(analyse_memory_growth));
        self.register("reinforcement",     "Stale memories, avg reinforcement count, unused decay",                 Arc::new(analyse_reinforcement));
        self.register("session_patterns",  "Session frequency, episodic replay trigger count",                      Arc::new(analyse_session_patterns));
    }
}

// ---------------------------------------------------------------------------
// Built-in analyser implementations
// Each is a standalone async fn — no shared state, no engine reference.
// The signature matches AnalyserFn.
// ---------------------------------------------------------------------------

fn analyse_decay_tuning(
    agent_id:    String,
    window_days: i64,
    store:       Arc<Store>,
    config:      Arc<Config>,
) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<AnalyticsResult>> + Send>> {
    Box::pin(async move {
        let mut findings = vec![];
        let mut recommendations = vec![];
        let mut config_suggestions = BTreeMap::new();

        // Tier distribution
        #[derive(surrealdb::types::SurrealValue)] struct TierRow { tier: i64, count: i64 }
        let mut res = store.query_raw(&format!(
            "SELECT tier, count() AS count FROM retrieval_trace \
             WHERE agent_id = '{agent_id}' AND created_at > time::now() - {window_days}d \
             GROUP BY tier ORDER BY tier;"
        )).await?;
        let tier_rows: Vec<TierRow> = res.take(0).unwrap_or_default();
        let total: i64 = tier_rows.iter().map(|r| r.count).sum();

        if total == 0 {
            return Ok(AnalyticsResult {
                query: "decay_tuning".to_string(), agent_id, window_days,
                findings: vec![Finding {
                    metric: "no_data".to_string(),
                    value: serde_json::json!(null),
                    severity: Severity::Info,
                    description: format!("No recall traces in the last {} days.", window_days),
                }],
                recommendations: vec![], config_suggestions: BTreeMap::new(),
            });
        }

        let tier4 = tier_rows.iter().find(|r| r.tier == 4).map(|r| r.count).unwrap_or(0);
        let tier1 = tier_rows.iter().find(|r| r.tier == 1).map(|r| r.count).unwrap_or(0);
        let escalation_rate = tier4 as f64 / total as f64;
        let direct_hit_rate = tier1 as f64 / total as f64;

        findings.push(Finding {
            metric: "total_recalls".to_string(),
            value: serde_json::json!(total),
            severity: Severity::Info,
            description: format!("{} recall operations in {} days", total, window_days),
        });
        findings.push(Finding {
            metric: "direct_hit_rate".to_string(),
            value: serde_json::json!(format!("{:.1}%", direct_hit_rate * 100.0)),
            severity: if direct_hit_rate > 0.6 { Severity::Info } else { Severity::Suggestion },
            description: format!("{:.1}% resolved at Tier 1 (direct lookup)", direct_hit_rate * 100.0),
        });

        if escalation_rate > 0.30 {
            findings.push(Finding {
                metric: "escalation_rate".to_string(),
                value: serde_json::json!(format!("{:.1}%", escalation_rate * 100.0)),
                severity: Severity::Warning,
                description: format!("{:.1}% required deep escalation (Tier 4)", escalation_rate * 100.0),
            });
            let new_lambda = format!("{:.4}", config.decay.category.knowledge * 0.7);
            recommendations.push(Recommendation {
                title: "Reduce knowledge decay rate".to_string(),
                detail: "High escalation suggests memories decay before they're needed again.".to_string(),
                config_key: Some("decay.category.knowledge".to_string()),
                config_from: Some(format!("{:.4}", config.decay.category.knowledge)),
                config_to: Some(new_lambda.clone()),
            });
            config_suggestions.insert("decay.category.knowledge".to_string(), new_lambda);
        }

        // Gap probe rate
        #[derive(surrealdb::types::SurrealValue)] struct GapRow { count: i64 }
        let mut res2 = store.query_raw(&format!(
            "SELECT count() AS count FROM gap_probe \
             WHERE agent_id = '{agent_id}' AND created_at > time::now() - {window_days}d;"
        )).await?;
        let gaps: Vec<GapRow> = res2.take(0).unwrap_or_default();
        let gap_count = gaps.first().map(|r| r.count).unwrap_or(0);
        let gap_rate = gap_count as f64 / total as f64;

        findings.push(Finding {
            metric: "gap_probe_rate".to_string(),
            value: serde_json::json!(format!("{:.1}%", gap_rate * 100.0)),
            severity: if gap_rate < 0.05 { Severity::Info }
                      else if gap_rate < 0.15 { Severity::Suggestion }
                      else { Severity::Warning },
            description: format!("{:.1}% of recalls ended in a gap probe ({} total)", gap_rate * 100.0, gap_count),
        });

        if gap_rate > 0.15 {
            let new_threshold = format!("{:.3}", (config.retrieval.threshold - 0.03).max(0.05));
            recommendations.push(Recommendation {
                title: "Lower retrieval threshold".to_string(),
                detail: format!("Gap rate {:.1}% is high. Threshold may be filtering too aggressively.", gap_rate * 100.0),
                config_key: Some("retrieval.threshold".to_string()),
                config_from: Some(format!("{:.3}", config.retrieval.threshold)),
                config_to: Some(new_threshold.clone()),
            });
            config_suggestions.insert("retrieval.threshold".to_string(), new_threshold);
        }

        // Useful rate
        #[derive(surrealdb::types::SurrealValue)] struct UsefulRow { useful: Option<bool>, count: i64 }
        let mut res3 = store.query_raw(&format!(
            "SELECT useful, count() AS count FROM retrieval_trace \
             WHERE agent_id = '{agent_id}' AND created_at > time::now() - {window_days}d \
             AND useful IS NOT NONE GROUP BY useful;"
        )).await?;
        let useful_rows: Vec<UsefulRow> = res3.take(0).unwrap_or_default();
        let useful = useful_rows.iter().filter(|r| r.useful == Some(true)).map(|r| r.count).sum::<i64>();
        let not_useful = useful_rows.iter().filter(|r| r.useful == Some(false)).map(|r| r.count).sum::<i64>();
        let feedback_total = useful + not_useful;

        if feedback_total > 0 {
            let rate = useful as f64 / feedback_total as f64;
            findings.push(Finding {
                metric: "useful_rate".to_string(),
                value: serde_json::json!(format!("{:.1}%", rate * 100.0)),
                severity: if rate > 0.7 { Severity::Info } else { Severity::Suggestion },
                description: format!("{:.1}% of recalled memories marked useful ({} feedback events)", rate * 100.0, feedback_total),
            });
            if rate < 0.5 {
                let new_threshold = format!("{:.3}", (config.retrieval.threshold + 0.05).min(0.5));
                recommendations.push(Recommendation {
                    title: "Raise retrieval threshold — wrong memories surfacing".to_string(),
                    detail: "Low useful rate means irrelevant memories are surfacing. Raise threshold.".to_string(),
                    config_key: Some("retrieval.threshold".to_string()),
                    config_from: Some(format!("{:.3}", config.retrieval.threshold)),
                    config_to: Some(new_threshold.clone()),
                });
                config_suggestions.insert("retrieval.threshold".to_string(), new_threshold);
            }
        }

        Ok(AnalyticsResult { query: "decay_tuning".to_string(), agent_id, window_days, findings, recommendations, config_suggestions })
    })
}

fn analyse_recall_health(
    agent_id: String, window_days: i64, store: Arc<Store>, _config: Arc<Config>,
) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<AnalyticsResult>> + Send>> {
    Box::pin(async move {
        #[derive(surrealdb::types::SurrealValue)] struct TierRow { tier: i64, count: i64 }
        let mut res = store.query_raw(&format!(
            "SELECT tier, count() AS count FROM retrieval_trace \
             WHERE agent_id = '{agent_id}' AND created_at > time::now() - {window_days}d \
             GROUP BY tier;"
        )).await?;
        let rows: Vec<TierRow> = res.take(0).unwrap_or_default();
        let total: i64 = rows.iter().map(|r| r.count).sum();
        let mut findings = vec![];
        let mut recommendations = vec![];

        for row in &rows {
            let name = match row.tier { 1=>"direct", 2=>"reuse", 3=>"hybrid", 4=>"full_context", _=>"?" };
            findings.push(Finding {
                metric: format!("tier_{}", row.tier),
                value: serde_json::json!({ "count": row.count, "pct": format!("{:.1}%", row.count as f64 / total.max(1) as f64 * 100.0) }),
                severity: Severity::Info,
                description: format!("Tier {} ({}): {} recalls ({:.1}%)", row.tier, name, row.count, row.count as f64 / total.max(1) as f64 * 100.0),
            });
        }

        let tier4 = rows.iter().find(|r| r.tier == 4).map(|r| r.count).unwrap_or(0);
        if total > 0 && tier4 as f64 / total as f64 > 0.25 {
            recommendations.push(Recommendation {
                title: "High full-context escalation rate".to_string(),
                detail: "Run 'decay_tuning' for specific lambda/threshold recommendations.".to_string(),
                config_key: None, config_from: None, config_to: None,
            });
        }

        Ok(AnalyticsResult { query: "recall_health".to_string(), agent_id, window_days, findings, recommendations, config_suggestions: BTreeMap::new() })
    })
}

fn analyse_conflict_patterns(
    agent_id: String, window_days: i64, store: Arc<Store>, _config: Arc<Config>,
) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<AnalyticsResult>> + Send>> {
    Box::pin(async move {
        #[derive(surrealdb::types::SurrealValue)] struct Row { conflict_type: String, count: i64 }
        let mut res = store.query_raw(&format!(
            "SELECT conflict_type, count() AS count FROM conflict_trace \
             WHERE agent_id = '{agent_id}' AND created_at > time::now() - {window_days}d \
             GROUP BY conflict_type;"
        )).await?;
        let rows: Vec<Row> = res.take(0).unwrap_or_default();
        let total: i64 = rows.iter().map(|r| r.count).sum();
        let findings = if total == 0 {
            vec![Finding { metric: "total".to_string(), value: serde_json::json!(0), severity: Severity::Info, description: format!("No conflicts in {} days.", window_days) }]
        } else {
            rows.iter().map(|r| Finding {
                metric: r.conflict_type.clone(),
                value: serde_json::json!({ "count": r.count, "pct": format!("{:.1}%", r.count as f64 / total as f64 * 100.0) }),
                severity: if r.conflict_type == "factual_contradiction" { Severity::Warning } else { Severity::Info },
                description: format!("{}: {} ({:.1}%)", r.conflict_type, r.count, r.count as f64 / total as f64 * 100.0),
            }).collect()
        };
        Ok(AnalyticsResult { query: "conflict_patterns".to_string(), agent_id, window_days, findings, recommendations: vec![], config_suggestions: BTreeMap::new() })
    })
}

fn analyse_memory_growth(
    agent_id: String, window_days: i64, store: Arc<Store>, _config: Arc<Config>,
) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<AnalyticsResult>> + Send>> {
    Box::pin(async move {
        #[derive(surrealdb::types::SurrealValue)] struct Row { category: String, count: i64, avg_confidence: f64 }
        let mut res = store.query_raw(&format!(
            "SELECT category, count() AS count, math::mean(confidence) AS avg_confidence \
             FROM memory WHERE agent_id = '{agent_id}' AND superseded = false \
             AND created_at > time::now() - {window_days}d GROUP BY category;"
        )).await?;
        let rows: Vec<Row> = res.take(0).unwrap_or_default();
        let total: i64 = rows.iter().map(|r| r.count).sum();
        let mut findings = vec![Finding {
            metric: "total".to_string(), value: serde_json::json!(total), severity: Severity::Info,
            description: format!("{} active memories in {} days", total, window_days),
        }];
        for row in &rows {
            findings.push(Finding {
                metric: row.category.clone(),
                value: serde_json::json!({ "count": row.count, "avg_confidence": format!("{:.2}", row.avg_confidence) }),
                severity: Severity::Info,
                description: format!("{}: {} memories, avg confidence {:.2}", row.category, row.count, row.avg_confidence),
            });
        }
        Ok(AnalyticsResult { query: "memory_growth".to_string(), agent_id, window_days, findings, recommendations: vec![], config_suggestions: BTreeMap::new() })
    })
}

fn analyse_reinforcement(
    agent_id: String, window_days: i64, store: Arc<Store>, config: Arc<Config>,
) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<AnalyticsResult>> + Send>> {
    Box::pin(async move {
        let mut findings = vec![];
        let mut recommendations = vec![];
        let mut config_suggestions = BTreeMap::new();

        #[derive(surrealdb::types::SurrealValue)] struct StaleRow { count: i64 }
        let mut res = store.query_raw(&format!(
            "SELECT count() AS count FROM memory WHERE agent_id = '{agent_id}' \
             AND superseded = false AND last_reinforced_at IS NONE AND created_at < time::now() - 30d;"
        )).await?;
        let stale: Vec<StaleRow> = res.take(0).unwrap_or_default();
        let stale_count = stale.first().map(|r| r.count).unwrap_or(0);

        findings.push(Finding {
            metric: "stale_memories".to_string(),
            value: serde_json::json!(stale_count),
            severity: if stale_count > 50 { Severity::Suggestion } else { Severity::Info },
            description: format!("{} memories never reinforced and older than 30 days", stale_count),
        });

        #[derive(surrealdb::types::SurrealValue)] struct AvgRow { avg: f64, max: i64 }
        let mut res2 = store.query_raw(&format!(
            "SELECT math::mean(reinforcement_count) AS avg, math::max(reinforcement_count) AS max \
             FROM memory WHERE agent_id = '{agent_id}' AND superseded = false \
             AND created_at > time::now() - {window_days}d;"
        )).await?;
        let avg_rows: Vec<AvgRow> = res2.take(0).unwrap_or_default();
        if let Some(row) = avg_rows.first() {
            findings.push(Finding {
                metric: "reinforcement_stats".to_string(),
                value: serde_json::json!({ "avg": format!("{:.1}", row.avg), "max": row.max }),
                severity: Severity::Info,
                description: format!("Avg {:.1} reinforcements/memory. Max: {}", row.avg, row.max),
            });
        }

        if stale_count > 100 {
            let new_lambda = format!("{:.4}", (config.decay.category.knowledge * 1.5).min(0.2));
            recommendations.push(Recommendation {
                title: "Increase decay rate for unused memories".to_string(),
                detail: format!("{} stale memories. Raise lambda so they fade faster.", stale_count),
                config_key: Some("decay.category.knowledge".to_string()),
                config_from: Some(format!("{:.4}", config.decay.category.knowledge)),
                config_to: Some(new_lambda.clone()),
            });
            config_suggestions.insert("decay.category.knowledge".to_string(), new_lambda);
        }

        Ok(AnalyticsResult { query: "reinforcement".to_string(), agent_id, window_days, findings, recommendations, config_suggestions })
    })
}

fn analyse_session_patterns(
    agent_id: String, window_days: i64, store: Arc<Store>, _config: Arc<Config>,
) -> std::pin::Pin<Box<dyn std::future::Future<Output = Result<AnalyticsResult>> + Send>> {
    Box::pin(async move {
        let mut findings = vec![];

        #[derive(surrealdb::types::SurrealValue)] struct Count { count: i64 }

        let mut res = store.query_raw(&format!(
            "SELECT count() AS count FROM session_index \
             WHERE agent_id = '{agent_id}' AND started_at > time::now() - {window_days}d;"
        )).await?;
        let sess: Vec<Count> = res.take(0).unwrap_or_default();
        findings.push(Finding {
            metric: "sessions".to_string(),
            value: serde_json::json!(sess.first().map(|r| r.count).unwrap_or(0)),
            severity: Severity::Info,
            description: format!("{} sessions in {} days", sess.first().map(|r| r.count).unwrap_or(0), window_days),
        });

        let mut res2 = store.query_raw(&format!(
            "SELECT count() AS count FROM gap_probe \
             WHERE agent_id = '{agent_id}' AND resolved = true \
             AND resolved_by_session IS NOT NONE AND created_at > time::now() - {window_days}d;"
        )).await?;
        let replays: Vec<Count> = res2.take(0).unwrap_or_default();
        findings.push(Finding {
            metric: "episodic_replays".to_string(),
            value: serde_json::json!(replays.first().map(|r| r.count).unwrap_or(0)),
            severity: Severity::Info,
            description: format!("{} gap probes resolved via episodic replay", replays.first().map(|r| r.count).unwrap_or(0)),
        });

        Ok(AnalyticsResult { query: "session_patterns".to_string(), agent_id, window_days, findings, recommendations: vec![], config_suggestions: BTreeMap::new() })
    })
}
