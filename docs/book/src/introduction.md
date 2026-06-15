# Introduction

**Agent-Memory** is an open memory layer for AI agents that behaves the way human
memory actually behaves — not the way software engineers typically model data storage.

> Embedded SurrealDB · Ebbinghaus decay · Episodic replay · Conflict resolution · Single Rust binary

It does not treat memory as a database lookup problem. It treats it as a cognitive
process: memories form, strengthen with use, fade without reinforcement, can be
reconstructed from temporal anchors, and conflict with each other in ways that require
resolution.

The system is grounded in [Autonomyx original research](./research/foundation.md) on
cognitive memory science, applied to the specific needs of AI agent runtimes.

## Why a book?

This book is the long-form documentation for Agent-Memory. If you want the
30-second pitch, read the [landing page](https://github.com/AGenNext/Agent-Memory).
If you want to understand *why* the system is built the way it is — and how to use
every part of it — start here.

| If you want to… | Go to |
|---|---|
| Install and run it | [Installation](./getting-started/installation.md) · [Quick start](./getting-started/quick-start.md) |
| Understand the memory model | [Memory model](./concepts/memory-model.md) |
| Learn how recall escalates | [Escalating recall](./concepts/escalating-recall.md) |
| See how conflicts are handled | [Conflict resolution](./concepts/conflict-resolution.md) |
| Read the API/MCP reference | [MCP tools](./reference/mcp-tools.md) |
| Tune the system | [Configuration](./reference/configuration.md) |
| Understand the science | [Research foundation](./research/foundation.md) |

## Core design principle

> **Optimize for resemblance to real-world memory behaviour, not architectural purity.**

Everything in Agent-Memory follows from that single commitment.
