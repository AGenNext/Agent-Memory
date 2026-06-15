# Installation

Agent-Memory embeds SurrealDB in-process. There is **no server to run** and **no
external dependency at runtime** — the database lives inside your binary.

## Rust

```bash
cargo add agent-memory
```

## Node.js / TypeScript

```bash
npm install @agentnxxt/agent-memory
```

## MCP server (Claude Desktop / Claude Code)

Agent-Memory ships an MCP server exposing [11 tools](../reference/mcp-tools.md).
Add it to your MCP config to give a Claude agent persistent, cognitively-modelled
memory. See the [MCP tools](../reference/mcp-tools.md) reference for the tool surface.

## Pre-built binaries

Pre-built binaries for all platforms are attached to each
[GitHub Release](https://github.com/AGenNext/Agent-Memory/releases):

- Linux x86_64 / aarch64
- macOS arm64 / x86_64
- Windows x86_64

## License

Apache-2.0 — see [LICENSE](https://github.com/AGenNext/Agent-Memory/blob/main/LICENSE).
