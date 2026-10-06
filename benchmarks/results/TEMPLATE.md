# Benchmark results — TEMPLATE

> Copy this file, fill in the environment block, paste the table emitted by
> `cargo run --release --example benchmark`, and commit alongside the commit
> hash it was run at. **Do not** type numbers in by hand for frameworks that
> were not actually run — leave them as `—`.

## Environment

- Agent-Memory commit: `<git rev-parse HEAD>`
- Date:                 `<YYYY-MM-DD>`
- Host:                 `<CPU / RAM / OS>`
- Storage backend:      `kv-mem` | `kv-rocksdb`
- Embeddings:           `off` | `<model>`
- Command:              `cargo run --release --example benchmark`

## Results — query set `identity_recall`

| Framework | Memories ingested | Queries | Recall@10 | Ingest mean (ms) | Ingest p95 (ms) | Recall mean (ms) | Recall p95 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| agent-memory | — | — | — | — | — | — | — |
| mem0 | — | — | — | — | — | — | — |
| zep | — | — | — | — | — | — | — |
| letta | — | — | — | — | — | — | — |
| langchain-memory | — | — | — | — | — | — | — |

Rows marked `—` have not been measured. agent-memory's row is populated by
running the harness; competitor rows require implementing an adapter (see
`benchmarks/README.md`).
