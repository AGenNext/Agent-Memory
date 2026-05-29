# Contributing to Agent-Memory

Thank you for your interest in contributing.

## Before you start

- Check open [issues](https://github.com/AGenNext/Agent-Memory/issues) — your idea may already be tracked
- For large changes, open an issue first to discuss the approach
- All contributions are licensed under Apache-2.0

## Setup

```bash
git clone https://github.com/AGenNext/Agent-Memory
cd Agent-Memory
cargo build
cargo test
```

Requires Rust 1.89+ and a C++ toolchain (for RocksDB).

## Design principles

These are non-negotiable. Read them before proposing changes.

**Episodic memories are immutable.** Raw conversation turns are canonical truth. They cannot be superseded, overwritten, or deleted except by hard purge (GDPR only). Any PR that modifies this will be closed.

**Forgetting is a feature.** The decay model is correct behaviour. PRs that make the agent remember more by default go against the design intent. The agent should store selectively, not exhaustively.

**Resemblance to real-world memory.** Every feature should map to how biological memory actually works. If you cannot cite a cognitive science basis for a proposed behaviour, reconsider it.

**The chat log outranks human recall.** The conflict resolution design (AgentStandsFirm) is intentional and grounded in Schacter's research on memory accuracy. PRs that make the agent more deferential to human claims over the log will not be accepted.

**Weights are empirically unvalidated.** Do not submit PRs with "better" hardcoded lambdas. The config system exists for a reason. Contribute real benchmark data if you have it.

## What we welcome

- Bug fixes with reproduction cases
- Performance improvements with benchmarks
- New analytics query types (register in `AnalyticsEngine`)
- Additional test coverage
- Documentation improvements
- Python SDK (PyO3 bindings) — highest priority open item
- Benchmark fixtures for AMB-001

## Pull request process

1. Fork the repo and create a branch from `main`
2. Write tests for new behaviour
3. Run `cargo fmt`, `cargo clippy`, `cargo test` — all must pass
4. Submit PR with a clear description of what changes and why
5. Link to any relevant issue or research

## Code style

- `cargo fmt` enforced by CI
- `cargo clippy -- -D warnings` enforced by CI
- No `unwrap()` in library code — use `?` and `anyhow`
- Public API items must have doc comments

## Reporting issues

Use [GitHub Issues](https://github.com/AGenNext/Agent-Memory/issues).
Include: Rust version, OS, reproduction steps, expected vs actual behaviour.

---

Built by [Autonomyx / OpenAutonomyx](https://openautonomyx.com) · Apache-2.0
