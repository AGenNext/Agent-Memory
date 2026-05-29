use chrono::{DateTime, Utc};

use crate::memory::types::{EpistemicStatus, Memory, MemoryCategory};

// ---------------------------------------------------------------------------
// Ebbinghaus decay model
//
// effective_confidence = base_confidence × e^(−λ × days_since_reinforcement)
//
// λ (decay_lambda) is category-specific:
//   fact        → 0.000  (never decays — externally verifiable)
//   instruction → 0.000  (behavioural directive — intentional, permanent)
//   identity    → 0.001  (very slow — name, role, stable attributes)
//   knowledge   → 0.020  (medium — decays without reinforcement)
//   uncertainty → 0.030  (medium — gets resolved or forgotten)
//   episodic    → 0.100  (fast — raw conversation, context specific)
//   context     → 0.500  (very fast — current session only)
//   assumption  → 0.050  (fades without evidence)
//   hearsay     → 0.080  (low trust, fades quickly)
//   inferred    → 0.030  (medium — like knowledge)
// ---------------------------------------------------------------------------

pub fn decay_lambda(category: &MemoryCategory, epistemic: &EpistemicStatus) -> f64 {
    // Facts and instructions never decay regardless of category
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
/// Uses stored decay_lambda and last_reinforced_at (falls back to known_time).
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

    // Clamp to [0.0, 1.0] — should never go negative but floating point
    decayed.clamp(0.0, 1.0)
}

/// Whether a memory is above the retrieval threshold after decay.
/// Memories below this are effectively gone from active recall.
/// The human may insist they exist — that triggers the gap protocol.
pub fn above_retrieval_threshold(memory: &Memory, now: DateTime<Utc>) -> bool {
    effective_confidence(memory, now) >= RETRIEVAL_THRESHOLD
}

/// Minimum effective confidence to surface in normal recall.
pub const RETRIEVAL_THRESHOLD: f64 = 0.15;

/// Minimum effective confidence to surface in full-context / escalating recall.
/// Lower — we're trying harder.
pub const ESCALATING_THRESHOLD: f64 = 0.05;

/// Reinforcement: reset decay by updating last_reinforced_at.
/// Returns the new reinforcement_count to store.
pub fn next_reinforcement_count(current: i64) -> i64 {
    current + 1
}

/// Confidence boost from reinforcement.
/// Each reinforcement nudges confidence slightly toward 1.0.
pub fn reinforced_confidence(current: f64) -> f64 {
    // Asymptotic: each reinforcement closes 10% of the gap to 1.0
    let gap = 1.0 - current;
    (current + gap * 0.10).clamp(0.0, 1.0)
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;

    fn mem_with(confidence: f64, lambda: f64, days_ago: i64) -> Memory {
        use crate::memory::types::*;
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
        let m = mem_with(0.9, 0.02, 90); // 3 months ago
        let ec = effective_confidence(&m, Utc::now());
        assert!(ec < 0.9, "should have decayed");
        assert!(ec > 0.1, "should not be gone yet");
    }

    #[test]
    fn context_decays_fast() {
        let m = mem_with(0.9, 0.50, 7); // 1 week ago
        let ec = effective_confidence(&m, Utc::now());
        assert!(ec < RETRIEVAL_THRESHOLD, "context from a week ago should be below threshold");
    }

    #[test]
    fn identity_barely_decays() {
        let m = mem_with(0.9, 0.001, 365); // 1 year ago
        let ec = effective_confidence(&m, Utc::now());
        assert!(ec > 0.6, "identity memory from a year ago should still be strong");
    }

    #[test]
    fn reinforcement_raises_confidence() {
        let c = reinforced_confidence(0.5);
        assert!(c > 0.5);
    }
}
