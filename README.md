# Agent-Memory

**Open memory layer for AI agents.**  
Embedded SurrealDB · Ebbinghaus decay · Episodic replay · Conflict resolution · Single Rust binary

[![Crates.io](https://img.shields.io/crates/v/agent-memory.svg)](https://crates.io/crates/agent-memory)
[![npm](https://img.shields.io/npm/v/@agentnxxt/agent-memory.svg)](https://www.npmjs.com/package/@agentnxxt/agent-memory)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/AGenNext/Agent-Memory?style=social)](https://github.com/AGenNext/Agent-Memory)

---

## What this is

Agent-Memory is a memory layer for AI agents that behaves the way human memory actually behaves — not the way software engineers typically model data storage.

It does not treat memory as a database lookup problem. It treats it as a cognitive process: memories form, strengthen with use, fade without reinforcement, can be reconstructed from temporal anchors, and conflict with each other in ways that require resolution.

The system is grounded in [Autonomyx original research](#research-foundation) on cognitive memory science, applied to the specific needs of AI agent runtimes.

---

## Quick start

```rust
use agent_memory::{AgentMemory, MemoryInput, MemoryCategory, RecallQuery};

// Boots embedded SurrealDB — no server, no install
let memory = AgentMemory::open("./data").await?;

// Store with Ebbinghaus decay configured per category
memory.remember(MemoryInput {
    agent_id:   "my-agent".to_string(),
    content:    "User prefers technically precise responses".to_string(),
    category:   MemoryCategory::Identity,
    importance: Some(0.9),
    ..Default::default()
}).await?;

// 5-tier escalating recall with gap protocol
let result = memory.recall_or_gap(query, human_insistence).await?;

match result {
    RecallOutcome::Found(r) => /* inject into prompt */,
    RecallOutcome::Gap(g)   => /* ask: g.suggested_prompt */,
}
```

---

## Install

```bash
# Rust
cargo add agent-memory

# Node.js / TypeScript
npm install @agentnxxt/agent-memory

# MCP server (Claude Desktop / Claude Code)
# Add to your MCP config — see docs
```

---

## Architecture

```
AgentMemory (public API)
  │
  ├── MemoryService          ← orchestration, decay, reinforcement
  │     ├── EscalatingRecall ← 5-tier retrieval + gap protocol
  │     ├── ConflictResolver ← 3 conflict types, decision log
  │     └── EpisodicReplay   ← session reconstruction from time anchor
  │
  ├── CortexSynthesiser      ← background sleep cycle (tokio task)
  ├── EvolutionWorker        ← background A-Mem evolution (tokio task)
  ├── AnalyticsEngine        ← generic registry-based telemetry
  │
  └── Store
        └── SurrealDB (embedded kv-rocksdb)
              ├── BM25 full-text search
              ├── HNSW vector search
              ├── Graph traversal (mem_edge)
              └── RocksDB (on-disk persistence)
```

Single process. No network. No external dependencies at runtime.

---

## Memory model

### Six categories

| Category | Lambda (default) | Description |
|---|---|---|
| `episodic` | 0.000 | Raw conversation turns. **Immutable canonical truth.** Never decays. |
| `identity` | 0.001 | Who the person is, how they operate. Very slow decay. |
| `knowledge` | 0.020 | Learned facts. Decays without reinforcement. |
| `context` | 0.500 | Current session state. Fades in days. |
| `instruction` | 0.000 | Behavioural directives. Never decays. |
| `uncertainty` | 0.030 | Known unknowns emitted by the reconciler. |

### Ebbinghaus decay

```
effective_confidence = base_confidence × e^(−λ × days_since_reinforcement)
```

Computed at retrieval time, not stored. Every successful recall reinforces the memory — resets the decay clock and nudges confidence upward. All weights are user-tunable via `config/default.toml`.

### Supersede-not-overwrite

Memory records are never overwritten. Updates create a new version with `derived_from` pointing to the old record. The supersession chain is always queryable. Episodic records (raw turns) cannot be superseded by any means — they are the canonical record.

### Five epistemic statuses

`fact` · `belief` · `assumption` · `hearsay` · `inferred`

Facts never decay regardless of category. The agent distinguishes what it knows from what it believes.

---

## Escalating recall

When normal recall finds nothing and the human insists something exists:

| Tier | Strategy |
|---|---|
| 1 | Direct lookup — category/scope filter, sub-ms |
| 2 | Hybrid BM25 + vector (HNSW) merged via Reciprocal Rank Fusion |
| 3 | Include superseded memories — maybe it was overwritten |
| 4 | Temporal expansion — search 7d, 30d, 90d, 365d windows by `known_time` |
| 5 | Scope relaxation — drop session and scope filters |
| → | Gap probe — returns `suggested_prompt` for the human |

If the human provides a time anchor, `EpisodicReplay` loads the complete session into active context — not just the fact, but everything that was happening at that time.

---

## Conflict resolution

Three conflict types, each handled differently:

**Misinterpretation** — "That's not what I meant"  
Agent stored an interpretation. Human corrects it. Agent accepts, versions the interpretation, preserves the original episodic turn.

**Agent stands firm** — "You told me X"  
Human claims the agent said something different. Agent shows the exact episodic record — verbatim, timestamped, session-linked. The chat log outranks human recall.

**Factual contradiction** — "The number was different"  
Human disputes a number from the chat log. Agent shows the exact line, sets `halt_reasoning = true`, stops that reasoning thread.

Every conflict resolution is logged in `conflict_trace` with full calibration reasoning. Queryable via the `decision_log` MCP tool.

---

## MCP tools (11)

`remember` · `recall` · `recall_or_gap` · `update` · `forget` · `reflect` · `inspect` · `replay_episode` · `conflict_resolve` · `decision_log` · `analytics`

---

## Analytics

```rust
// Built-in queries — extensible registry, no code changes needed
memory.analytics("my-agent", "decay_tuning", 30).await?
// → gap probe rate, tier distribution, config_suggestions: {"decay.category.knowledge": "0.014"}

memory.analytics("my-agent", "summary", 30).await?
// → all analyses merged, highest severity first

memory.analytics("my-agent", "available", 30).await?
// → lists all registered query names
```

Returns `config_suggestions` — exact `config.toml` changes to apply. Human copies them in, restarts. Done.

---

## Configuration

All decay weights, thresholds, and intervals are tunable via `config/default.toml`:

```toml
[decay.category]
identity    = 0.001   # very slow — name, role
knowledge   = 0.020   # medium — decays without use
episodic    = 0.100   # fast — raw conversation
context     = 0.500   # very fast — current session
instruction = 0.000   # never — behavioural directives

[retrieval]
threshold            = 0.15   # minimum confidence for normal recall
escalating_threshold = 0.05   # minimum for deep search

[reconciler]
confidence_floor       = 0.40  # below this → emit uncertainty instead of superseding
human_statement_trust  = 0.90  # direct human statement in current turn
```

The weights are Version 1 defaults — empirically unvalidated. The analytics tool collects the signal to tune them. There are no universally correct values.

---

## Research foundation

Agent-Memory is an [Autonomyx](https://openautonomyx.com) original research project. The memory model is grounded in peer-reviewed cognitive science, not in software engineering conventions:

| Source | Contribution to Agent-Memory |
|---|---|
| **Schacter, Harvard (2025)** — *How Memory Works (and Doesn't)* | Memory is reconstruction not replay. Confidence ≠ accuracy. Source misattribution is the core false memory mechanism. Basis for `AgentStandsFirm` conflict type. |
| **Schacter (2001)** — *Seven Sins of Memory* | Transience, misattribution, suggestibility, bias — each maps to a specific system behaviour. Forgetting as adaptive feature. |
| **QBI, University of Queensland** — *How Are Memories Formed?* | Synaptic plasticity: active connections strengthen, unused weaken. Basis for reinforcement-on-recall and Ebbinghaus lambda. Sleep replay = CortexSynthesiser. |
| **Psychology Today** — *How Memory Works* | Reconsolidation: every retrieval makes memory temporarily rewritable. Basis for `reconsolidation_note` on retrieval traces. |
| **Scientific American** — *Elephants Never Forget* | Memory serves survival. Older memories with survival value are more durable. Basis for `importance` field and selective storage principle. |
| **BBC Future / HSAM research** | Perfect memory is pathological. Forgetting is a feature. Basis for the design principle: the agent should not store everything. |
| **Farnam Street** — *Mental Models* | Agent should build a mental model of where things live, not memorise contents. Basis for CortexSynthesiser knowledge brief as a map, not a transcript. |
| **Spectron (SurrealDB)** | 6 typed categories, tri-temporal clocks, provenance-as-data, supersede-not-overwrite, four-tier retrieval |
| **A-Mem (paper)** | Memory evolution via event queue — EvolutionWorker |
| **Spacebot Cortex** | Background-synthesised working memory layers — CortexSynthesiser |

The core design principle: **optimize for resemblance to real-world memory behaviour, not architectural purity.**

---

## Releases

Pre-built binaries for all platforms are attached to each [GitHub Release](https://github.com/AGenNext/Agent-Memory/releases):

- Linux x86_64 / aarch64
- macOS arm64 / x86_64  
- Windows x86_64

---

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

Apache-2.0 — see [LICENSE](LICENSE)

---

<p align="center">
  Built by <a href="https://openautonomyx.com">Autonomyx / OpenAutonomyx</a> · 
  Part of the <a href="https://github.com/AGenNext">AGenNext</a> ecosystem
  <br><br>
  <a href="https://github.com/AGenNext/Agent-Memory">⭐ Star us on GitHub</a>
</p>
