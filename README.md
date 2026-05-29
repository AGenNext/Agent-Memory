# Agent-Memory

Production memory SDK and contracts for AGenNext.

SurrealDB is the durable source of truth for memory, graph, vector retrieval,
traces, and runtime state that belongs to memory.

---

## Design sources

| Source | What it contributes | Status |
|--------|--------------------|----|
| **Spectron (SurrealDB)** | 6 typed categories, tri-temporal clocks, provenance-as-data, supersede-not-overwrite, calibration, retrieval traces as first-class memory, four-tier query ladder | **MUST — fully implemented** |
| **A-Mem (paper)** | Memory evolution: when a new memory is written, related memories get their context/tags updated via an evolution queue | **Real value — implemented via DEFINE EVENT + EvolutionWorker** |
| **Spacebot Cortex** | Background-synthesised `working_memory` table with 5 layers; never written per LLM call | **Real value — implemented via CortexSynthesiser** |
| agentmemory | Dev-time coding agent sidecar | Not adopted — wrong layer |
| AgeMem (paper) | RL-trained LTM+STM | Not adopted — requires model fine-tuning; tool taxonomy already covered |

---

## Architecture

```
Agent-Runtime / Agent-Chat / Agent-Dashboard
  ↓
MemoryService            ← high-level API (remember, recall, update, forget)
  ↓
SurrealMemoryClient      ← all DB operations, RRF merge, tri-temporal queries
  ↓
SurrealDB Cloud          ← ACID, HNSW vector, BM25 FTS, MVCC, graph RELATE
```

Background services (run on schedule, not per LLM call):

```
EvolutionWorker    ← drains evolution_queue; links + evolves related memories (A-Mem)
CortexSynthesiser  ← maintains 5 working_memory layers (Spacebot Cortex)
```

---

## Schema tables

| Table | Purpose |
|-------|---------|
| `memory` | Core memory record — 6 categories, tri-temporal, provenance, calibration |
| `mem_edge` | Graph relations between memories — 5 edge types |
| `retrieval_trace` | Every read recorded; ranker reads its own history |
| `decision_trace` | Audit trail for agent decisions |
| `working_memory` | Cortex: 5 synthesised layers per agent |
| `evolution_queue` | A-Mem: jobs queued by DEFINE EVENT on every memory write |

---

## Memory categories (Spectron)

| Category | Retention | Use |
|----------|-----------|-----|
| `episodic` | Long | Raw conversational record — source of truth |
| `identity` | Long | Durable facts about agent/user |
| `knowledge` | Medium | Learnt things; decays without reinforcement |
| `context` | Short | Active working context for current session |
| `instruction` | Long | Behavioural directives; applied at prompt assembly |
| `uncertainty` | Medium | Explicit "we don't know yet" — emitted by reconciler |

---

## Tri-temporal model (Spectron)

Three independent clocks on every memory:

| Clock | What it answers | How stored |
|-------|----------------|-----------|
| **system_time** | What did the DB look like at instant T? | SurrealDB MVCC — use `VERSION` queries |
| **known_time** | When did we first believe this fact? | `known_time` field — `VALUE time::now()` |
| **valid_time** | When did this assertion hold in the world? | `valid_time_start` + `valid_time_end` fields |

---

## Provenance fields (Spectron)

Every memory row carries:

```
source_kind    agent_turn | user_turn | document | reflection | elaboration | consolidation | tool_output | external
source_ref     turn_id or doc_id
source_trust   0.0–1.0 (admin doc > user assertion > reflection > elaboration)
derived_from   array of record IDs this memory was synthesised from
confidence     0.0–1.0 reconciler posterior
```

---

## Supersede-not-overwrite (Spectron)

`MemoryService.update()` never overwrites. It:
1. Sets `superseded=true`, `valid_time_end=now` on the old record
2. Creates a new record with `derived_from=[old_id]`
3. Creates a `mem_edge` of kind `updates` (new → old)
4. Sets `superseded_by` on old record

Full supersession lineage is queryable via `MemoryService.get_history()`.

---

## Four-tier retrieval (Spectron)

| Tier | When | Latency |
|------|------|---------|
| 1 — Direct lookup | Typed questions ("what is my role?") | Sub-ms |
| 2 — Response reuse | Same query, cached answer still valid | Tens of ms |
| 3 — Hybrid | Vector (HNSW cosine) + BM25 merged via RRF | Hundreds of ms |
| 4 — Full context | Thin results, broader sweep + HyDE rewrite | Higher cost |

Every retrieval writes a `retrieval_trace`. Feedback (`useful`, `correction`) is
stored on the trace and feeds back into future rankings.

---

## Working memory layers (Spacebot Cortex)

| Layer | Rebuilt when | Content |
|-------|-------------|---------|
| `identity_context` | On identity memory change | Stable agent identity briefing |
| `intraday_synthesis` | Hourly | Compressed narrative of today's events |
| `daily_rollup` | Midnight | Day summary replacing intraday |
| `cross_agent_map` | On cross-agent activity | Activity snapshot across agents |
| `knowledge_brief` | On knowledge graph change | Synthesised knowledge briefing |

Never written per LLM call. Injected into prompt by `MemoryService.get_context()`.

---

## Memory evolution (A-Mem)

On every `CREATE` to the `memory` table, `DEFINE EVENT memory_created` fires and
queues an `evolution_queue` job. `EvolutionWorker.run_once()`:

1. Claims a batch of pending jobs
2. Finds top-k related memories via hybrid search
3. Runs `MemoryService.reconcile()` — links + contradiction detection
4. Calls optional `evolve_fn(new_memory, related)` → updates context/keywords/tags
5. Marks jobs done

`evolve_fn` is injected — can be an LLM call or rule-based. The SDK does not own
the LLM call.

---

## Quick start

```python
from agent_memory import SurrealMemoryClient, MemoryService, MemoryCategory

client = SurrealMemoryClient(
    url="wss://schemadb-06ehsj292ppah8kbsk9pmnjjbc.aws-aps1.surreal.cloud",
    namespace="agnxxt",
    database="agent_memory",
    username="...",
    password="...",
)
await client.connect()

svc = MemoryService(client)

# Write
mem = await svc.remember(
    agent_id="agent:orchestrator-01",
    content="User prefers concise responses with code examples.",
    category=MemoryCategory.IDENTITY,
    importance=0.9,
)

# Read
result = await svc.recall(
    agent_id="agent:orchestrator-01",
    query_text="what does the user prefer?",
    top_k=5,
)

# Get assembled Cortex context for prompt injection
context_layers = await svc.get_context("agent:orchestrator-01")

# Supersede (never overwrite)
old, new = await svc.update(
    old_memory_id=mem.id,
    new_content="User prefers bullet-point responses with Python examples.",
)

# Forget (soft by default; purge=True for hard delete)
await svc.forget(mem.id)
```

---

## Scope

Agent-Memory owns:
- memory contracts (models.py)
- SurrealDB memory backend (client.py)
- graph memory (mem_edge, get_related_memories)
- vector memory (HNSW index, hybrid retrieval)
- GraphRAG contracts (retrieval traces, RRF)
- decision traces
- runtime memory APIs (MemoryService)
- background services (EvolutionWorker, CortexSynthesiser)
- SurrealDB schemas (schemas/surrealdb/memory.surql)

Agent-Memory does not own:
- sample agents
- framework comparisons
- runtime execution
- LangGraph adapters
- UI
- provider adapters
- LLM calls (injected via evolve_fn / synthesise_fn)
