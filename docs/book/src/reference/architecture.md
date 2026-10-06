# Architecture

Agent-Memory runs as a single process. No network. No external dependencies at runtime.

```text
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

## Components

| Component | Responsibility |
|---|---|
| **MemoryService** | Orchestrates storage, decay computation, and reinforcement-on-recall. |
| **EscalatingRecall** | The [5-tier retrieval](../concepts/escalating-recall.md) ladder and gap protocol. |
| **ConflictResolver** | The [three conflict types](../concepts/conflict-resolution.md) and the decision log. |
| **EpisodicReplay** | Reconstructs a complete past session from a time anchor. |
| **CortexSynthesiser** | Background "sleep cycle" (tokio task) that synthesises a knowledge brief — a map of where things live, not a transcript. |
| **EvolutionWorker** | Background [A-Mem](../research/foundation.md) memory evolution driven by an event queue. |
| **AnalyticsEngine** | Generic, registry-based telemetry — see [Analytics](./analytics.md). |
| **Store / SurrealDB** | Embedded `kv-rocksdb` engine providing BM25 full-text, HNSW vector search, graph traversal over `mem_edge`, and on-disk RocksDB persistence. |

## Why embedded

Boots in-process, persists to disk via RocksDB, and exposes full-text, vector, and
graph search through one engine. That keeps the deployment story trivial — a single
binary with no sidecar database to provision, secure, or keep alive.
