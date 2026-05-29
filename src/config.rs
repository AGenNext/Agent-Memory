use std::path::Path;

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Top-level config
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    #[serde(default)]
    pub decay:      DecayConfig,

    #[serde(default)]
    pub retrieval:  RetrievalConfig,

    #[serde(default)]
    pub reconciler: ReconcilerConfig,

    #[serde(default)]
    pub cortex:     CortexConfig,

    #[serde(default)]
    pub store:      StoreConfig,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            decay:      DecayConfig::default(),
            retrieval:  RetrievalConfig::default(),
            reconciler: ReconcilerConfig::default(),
            cortex:     CortexConfig::default(),
            store:      StoreConfig::default(),
        }
    }
}

// ---------------------------------------------------------------------------
// Decay config
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecayConfig {
    #[serde(default)]
    pub category:  CategoryDecay,

    #[serde(default)]
    pub epistemic: EpistemicDecay,
}

impl Default for DecayConfig {
    fn default() -> Self {
        Self {
            category:  CategoryDecay::default(),
            epistemic: EpistemicDecay::default(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CategoryDecay {
    pub episodic:    f64,
    pub identity:    f64,
    pub knowledge:   f64,
    pub context:     f64,
    pub instruction: f64,
    pub uncertainty: f64,
}

impl Default for CategoryDecay {
    fn default() -> Self {
        Self {
            episodic:    0.100,
            identity:    0.001,
            knowledge:   0.020,
            context:     0.500,
            instruction: 0.000,
            uncertainty: 0.030,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EpistemicDecay {
    pub fact:       f64,
    pub belief:     f64,
    pub assumption: f64,
    pub hearsay:    f64,
    pub inferred:   f64,
}

impl Default for EpistemicDecay {
    fn default() -> Self {
        Self {
            fact:       0.000,
            belief:     0.020,
            assumption: 0.050,
            hearsay:    0.080,
            inferred:   0.030,
        }
    }
}

// ---------------------------------------------------------------------------
// Retrieval config
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetrievalConfig {
    pub threshold:            f64,
    pub escalating_threshold: f64,
}

impl Default for RetrievalConfig {
    fn default() -> Self {
        Self {
            threshold:            0.15,
            escalating_threshold: 0.05,
        }
    }
}

// ---------------------------------------------------------------------------
// Reconciler config
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReconcilerConfig {
    pub confidence_floor:        f64,
    pub human_statement_trust:   f64,
}

impl Default for ReconcilerConfig {
    fn default() -> Self {
        Self {
            confidence_floor:      0.40,
            human_statement_trust: 0.90,
        }
    }
}

// ---------------------------------------------------------------------------
// Cortex config
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CortexConfig {
    pub intraday_interval_secs:  u64,
    pub evolution_interval_secs: u64,
}

impl Default for CortexConfig {
    fn default() -> Self {
        Self {
            intraday_interval_secs:  3600,
            evolution_interval_secs: 30,
        }
    }
}

// ---------------------------------------------------------------------------
// Store config
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StoreConfig {
    pub max_recall_results: usize,
    pub search_candidates:  usize,
}

impl Default for StoreConfig {
    fn default() -> Self {
        Self {
            max_recall_results: 100,
            search_candidates:  20,
        }
    }
}

// ---------------------------------------------------------------------------
// Loading
// ---------------------------------------------------------------------------

impl Config {
    /// Load from a TOML file. Missing fields fall back to defaults.
    /// If no file exists, returns full defaults.
    pub fn load(path: &Path) -> Result<Self> {
        if !path.exists() {
            tracing::info!(
                "config file {:?} not found — using defaults. \
                 Copy config/default.toml to customise.",
                path
            );
            return Ok(Self::default());
        }

        let content = std::fs::read_to_string(path)
            .with_context(|| format!("read config file {:?}", path))?;

        let config: Self = toml::from_str(&content)
            .with_context(|| format!("parse config file {:?}", path))?;

        tracing::info!("loaded config from {:?}", path);
        Ok(config)
    }

    /// Write the default config to a path (for --init-config CLI flag).
    pub fn write_default(path: &Path) -> Result<()> {
        let default = Self::default();
        let content = toml::to_string_pretty(&default)
            .context("serialise default config")?;
        std::fs::write(path, content)
            .with_context(|| format!("write config to {:?}", path))?;
        Ok(())
    }
}

// ---------------------------------------------------------------------------
// Convenience accessors used by decay.rs
// ---------------------------------------------------------------------------

impl Config {
    pub fn lambda_for_category(
        &self,
        category:  &crate::memory::types::MemoryCategory,
        epistemic: &crate::memory::types::EpistemicStatus,
    ) -> f64 {
        use crate::memory::types::{EpistemicStatus, MemoryCategory};

        // Epistemic overrides take priority
        let epistemic_lambda = match epistemic {
            EpistemicStatus::Fact       => return self.decay.epistemic.fact,
            EpistemicStatus::Hearsay    => self.decay.epistemic.hearsay,
            EpistemicStatus::Assumption => self.decay.epistemic.assumption,
            EpistemicStatus::Inferred   => self.decay.epistemic.inferred,
            EpistemicStatus::Belief     => self.decay.epistemic.belief,
        };

        // Category base rate
        let category_lambda = match category {
            MemoryCategory::Instruction  => return 0.0, // never decays
            MemoryCategory::Identity     => self.decay.category.identity,
            MemoryCategory::Knowledge    => self.decay.category.knowledge,
            MemoryCategory::Uncertainty  => self.decay.category.uncertainty,
            MemoryCategory::Episodic     => self.decay.category.episodic,
            MemoryCategory::Context      => self.decay.category.context,
        };

        // Take the higher (faster decaying) of the two
        // A hearsay knowledge memory decays at hearsay rate, not knowledge rate
        epistemic_lambda.max(category_lambda)
    }

    pub fn retrieval_threshold(&self) -> f64 {
        self.retrieval.threshold
    }

    pub fn escalating_threshold(&self) -> f64 {
        self.retrieval.escalating_threshold
    }

    pub fn confidence_floor(&self) -> f64 {
        self.reconciler.confidence_floor
    }

    pub fn human_statement_trust(&self) -> f64 {
        self.reconciler.human_statement_trust
    }
}
