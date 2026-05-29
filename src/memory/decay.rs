use chrono::{DateTime, Utc};

use crate::memory::types::{EpistemicStatus, Memory, MemoryCategory};

// ---------------------------------------------------------------------------
// Ebbinghaus decay model — config-driven
//
// effective_confidence = base_confidence × e^(−lambda × days_since_reinforcement)
//
// Lambda values come from Config, not hardcoded here.
// Users tune them in config.toml based on their usage patterns.
// These defaults are Version 1 starting points — they will be wrong
// for many use cases. Tune empirically with real interaction data.
//
// Default lambdas (overrideable in config.toml):
//   fact        → 0.000  (never decays — externally verifiable)
//   instruction → 0.000  (behavioural directive — permanent)
//   identity    → 0.001  (very slow — name, role, stable attributes)
//   knowledge   → 0.020  (medium — decays without reinforcement)
//   uncertainty → 0.030  (medium — gets resolved or forgotten)
//   episodic    → 0.100  (fast — raw conversation, context specific)
//   context     → 0.500  (very fast — current session only)
//   assumption  → 0.050  (fades without evidence)
//   hearsay     → 0.080  (low trust, fades quickly)
//   inferred    → 0.030  (medium — like knowledge)
// ---------------------------------------------------------------------------

/// Compute the decay lambda for a memory using config values.
/// Called at memory creation time to set the stored decay_lambda field.
pub fn decay_lambda_from_config(
    config:    &crate::config::Config,
    category:  &MemoryCategory,
    epistemic: &EpistemicStatus,
) -> f64 {
    config.lambda_for_category(category, epistemic)
}

/// Fallback: compute decay lambda without config (uses hardcoded defaults).
/// Used in tests and when config is not available.
pub fn decay_lambda(category: &MemoryCategory, epistemic: &EpistemicStatus) -> f64 {
    // Epistemic status overrides
    match epistemic {
        EpistemicStatus::Fact        => return 0.0,
        EpistemicStatus::Hearsay     => return 0.08,
        EpistemicStatus::Assumption  => return 0.05,
        EpistemicStatus::Inferred    => return 0.03,
        _ => {}
    }

    match category {
        MemoryCategory::Instruction  => 0.000,
        MemoryCategory::Identity     => 0.001,
        MemoryCategory::Knowledge    => 0.020,
        MemoryCategory::Uncertainty  => 0.030,
        MemoryCategory::Episodic     => 0.100,
        MemoryCategory::Context      => 0.500,
    }
}

/// Compute effective confidence at query time.
/// Uses the stored decay_lambda from the memory record (set at creation).
/// This means each memory uses the lambda that was configured when it was created.
pub fn effective_confidence(memory: &Memory, now: DateTime<Utc>) -> f64 {
    let lambda = memory.decay_lambda;

    // No decay
    if lambda == 0.0 {
        return memory.confidence;
    }

    // Reference point: last reinforced, or when we first knew it
    let reference = memory
        .last_reinforced_at
        .or(memory.known_time)
        .unwrap_or(now);

    let days = (now - reference).num_seconds() as f64 / 86_400.0;
    let days = days.max(0.0);

    let decayed = memory.confidence * (-lambda * days).exp();

    // Clamp to [0.0, 1.0]
    decayed.clamp(0.0, 1.0)
}

/// Whether a memory is above the retrieval threshold after decay.
pub fn above_retrieval_threshold(
    memory:    &Memory,
    now:       DateTime<Utc>,
    threshold: f64,
) -> bool {
    effective_confidence(memory, now) >= threshold
}

/// Default retrieval threshold — used when config is not available.
pub const DEFAULT_RETRIEVAL_THRESHOLD: f64 = 0.15;

/// Default escalating threshold — used when config is not available.
pub const DEFAULT_ESCALATING_THRESHOLD: f64 = 0.05;

/// Reinforcement: reset decay by updating last_reinforced_at.
pub fn next_reinforcement_count(current: i64) -> i64 {
    current + 1
}

/// Confidence boost from reinforcement.
/// Each reinforcement nudges confidence slightly toward 1.0.
/// Asymptotic: closes 10% of gap to 1.0 per reinforcement.
pub fn reinforced_confidence(current: f64) -> f64 {
    let gap = 1.0 - current;
    (current + gap * 0.10).clamp(0.0, 1.0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;
    use crate::memory::types::*;

    fn mem_with(confidence: f64, lambda: f64, days_ago: i64) -> Memory {
        Memory {
            id: None,
            category: MemoryCategory::Knowledge,
            content: String::new(),
            summary: None,
            agent_id: String::new(),
            session_id: None,
            scope: MemoryScope::Agent,
            known_time: Some(Utc::now() - Duration::days(days_ago)),
            valid_time_start: None,
            valid_time_end: None,
            source_kind: SourceKind::AgentTurn,
            source_ref: None,
            source_trust: 0.7,
            derived_from: None,
            confidence,
            importance: 0.5,
            superseded: false,
            superseded_at: None,
            superseded_by: None,
            keywords: None,
            tags: None,
            evolved_at: None,
            embedding: None,
            created_at: None,
            updated_at: None,
            epistemic_status: EpistemicStatus::Belief,
            last_reinforced_at: None,
            reinforcement_count: 0,
            decay_lambda: lambda,
        }
    }

    #[test]
    fn fact_never_decays() {
        let mut m = mem_with(0.9, 0.0, 365);
        m.epistemic_status = EpistemicStatus::Fact;
        assert_eq!(effective_confidence(&m, Utc::now()), 0.9);
    }

    #[test]
    fn knowledge_decays_over_months() {
        let m = mem_with(0.9, 0.02, 90);
        let ec = effective_confidence(&m, Utc::now());
        assert!(ec < 0.9, "should have decayed");
        assert!(ec > 0.1, "should not be gone yet");
    }

    #[test]
    fn context_decays_fast() {
        let m = mem_with(0.9, 0.50, 7);
        let ec = effective_confidence(&m, Utc::now());
        assert!(ec < DEFAULT_RETRIEVAL_THRESHOLD, "context from a week ago should be below threshold");
    }

    #[test]
    fn identity_barely_decays() {
        let m = mem_with(0.9, 0.001, 365);
        let ec = effective_confidence(&m, Utc::now());
        assert!(ec > 0.6, "identity memory from a year ago should still be strong");
    }

    #[test]
    fn reinforcement_raises_confidence() {
        let c = reinforced_confidence(0.5);
        assert!(c > 0.5);
    }

    #[test]
    fn config_overrides_defaults() {
        let mut config = crate::config::Config::default();
        // Set identity to decay much faster
        config.decay.category.identity = 0.1;
        let lambda = config.lambda_for_category(
            &MemoryCategory::Identity,
            &EpistemicStatus::Belief,
        );
        // belief (0.020) < identity_override (0.100), so identity wins
        assert!((lambda - 0.1).abs() < 0.001);
    }
}
