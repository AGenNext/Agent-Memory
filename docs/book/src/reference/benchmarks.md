# Benchmarks

A reproducible memory benchmark harness lives in
[`benchmarks/`](https://github.com/AGenNext/Agent-Memory/tree/main/benchmarks). It
drives the public API against synthetic multi-turn conversation fixtures and measures
**recall@10** plus ingest/recall latency.

```bash
cargo run --release --example benchmark
# write a markdown report:
cargo run --release --example benchmark -- --out benchmarks/results/agent-memory.md
```

## What it measures

| Metric | What it measures |
|---|---|
| Recall@10 | Fraction of queries where the correct memory is in the top 10 retrieved |
| Ingest mean / p95 | Per-`remember` latency |
| Recall mean / p95 | Per-`recall` latency |

## Integrity rule

The harness defines a `MemoryFramework` adapter trait so other memory frameworks (Mem0,
Zep, Letta, LangChain memory) can be benchmarked apples-to-apples on the same fixtures
and scoring.

> **No comparative numbers are published until they are actually measured.**

Every number reported is measured on the run that produced it. See
[`benchmarks/README.md`](https://github.com/AGenNext/Agent-Memory/blob/main/benchmarks/README.md)
for the methodology, the adapter contract, and the reproducibility checklist.
