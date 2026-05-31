# Agent-Memory benchmarks

This directory holds the **memory benchmark harness**: fixtures, a query set,
and a runner that measures recall accuracy and latency by driving the public
`agent_memory` API.

> **Integrity note.** Every number this harness reports is *measured on the
> run that produced it*. There are no hard-coded or estimated results checked
> into this repo. Comparative numbers against other frameworks (Mem0, Zep,
> Letta, LangChain memory) are **not** published until an adapter for each
> framework has actually been run — see [Comparing frameworks](#comparing-frameworks).
> Rows without an adapter render as `—`, never as an invented figure.

## Layout

```
benchmarks/
  README.md                      ← this file (methodology)
  memory/fixtures/
    conversations/*.json         ← synthetic multi-turn conversations + gold answers
    queries/*.json               ← query sets with gold substrings for scoring
  results/                       ← generated reports (gitignored except templates)
    TEMPLATE.md                  ← empty results table, filled by real runs
```

The runner itself lives at [`examples/benchmark.rs`](../examples/benchmark.rs).

## Running it

```sh
# Build + run against the in-memory store, print a markdown table:
cargo run --release --example benchmark

# Also write the report to a file:
cargo run --release --example benchmark -- --out benchmarks/results/agent-memory.md
```

The harness:

1. Loads every conversation in `memory/fixtures/conversations/`.
2. Ingests each turn as a memory under the benchmark agent id (`test-agent`),
   timing each `remember` call.
3. Runs every query in the query set via `recall(top_k = 10)`, timing each call.
4. Scores each query, then prints a results table.

## Metrics

| Metric | Definition |
|---|---|
| **Recall@10** | Fraction of queries for which at least one of the top-10 retrieved memories contains the gold answer (case-insensitive substring of `gold` or any `gold_alts`). |
| **Ingest mean / p95 (ms)** | Wall-clock time per `remember` call. |
| **Recall mean / p95 (ms)** | Wall-clock time per `recall` call. |

Latency is **machine-relative** — it depends on the host, the storage backend
(in-memory vs RocksDB), and whether embeddings are configured. Always report
the environment alongside the numbers. Recall@10 is the portable, comparable
metric.

### Scoring rationale

We score on substring containment of a curated gold answer rather than exact
match, because retrieval surfaces the *memory* (the original turn text), not a
generated answer. `gold_alts` captures acceptable phrasings so the score
reflects "did the right memory surface", not prompt wording. This keeps the
metric framework-neutral: any framework that returns the source text is scored
identically.

## Fixtures

Each conversation fixture is a short, synthetic dialogue with a `gold_answers`
block. Conversations are designed to exercise specific memory behaviours:

| Fixture | Domain | Exercises |
|---|---|---|
| `PA-01` | Personal assistant | Misinterpretation conflict + supersession chain |
| `PA-02` | Personal assistant | Multi-fact identity recall (timezone, feedback, comms) |
| `PA-03` | Personal assistant | Single stable preference recall |
| `ENG-01` | Engineering | Five identity facts in one conversation |
| `ENG-02` | Engineering | Instruction/process recall (breaking-change policy) |
| `PM-01` | Project management | Identity facts incl. a numeric value |
| `PM-02` | Project management | Two process preferences |
| `CS-01` | Customer support | Two operational facts |
| `RS-01` | Research | Methodology recall |

All fixtures are hand-authored and synthetic — no real user data.

## Comparing frameworks

agent-memory runs **in-process**, so the harness measures it directly. Other
memory frameworks run as external services with their own API keys and network
requirements, so they are not bundled here. To add one and get a real,
apples-to-apples comparison:

1. Implement the `MemoryFramework` trait (in `examples/benchmark.rs`) against
   the target framework's client:
   - `remember(agent_id, speaker, text)` — store one turn.
   - `recall(agent_id, query, top_k)` — return the text of the top-k memories.
2. Add it to the list of frameworks the harness runs.
3. Keep the comparison fair:
   - Same fixtures, same query set, same `top_k`.
   - Same scoring (substring containment — no per-framework answer generation).
   - Disclose the storage backend and whether embeddings/LLM calls are used,
     since those dominate latency.
   - Run on the same machine in the same session; report the environment.

Until a framework has actually been run through this harness, it appears in the
results table as `—`. **Do not** fill those cells with numbers from a vendor's
own marketing or a different benchmark — that is exactly the kind of
non-reproducible figure this harness exists to avoid.

## Reproducibility checklist

When publishing results, include:

- [ ] Commit hash of agent-memory.
- [ ] Host CPU / RAM / OS.
- [ ] Storage backend (`kv-mem` vs `kv-rocksdb`).
- [ ] Whether embeddings were configured (affects vector recall).
- [ ] The exact command used.
- [ ] The query set name and fixture count.
