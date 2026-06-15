# MCP tools

Agent-Memory exposes **11 MCP tools** for use from Claude Desktop, Claude Code, or any
MCP-compatible runtime.

| Tool | Purpose |
|---|---|
| `remember` | Store a new memory with category, importance, and epistemic status. |
| `recall` | Normal retrieval — direct lookup plus hybrid search. |
| `recall_or_gap` | Recall that [escalates through five tiers](../concepts/escalating-recall.md) and returns a gap probe if nothing is found. |
| `update` | Supersede a memory — creates a new version, preserves the old one. |
| `forget` | Remove a memory (episodic records cannot be removed). |
| `reflect` | Trigger background synthesis / reflection over stored memories. |
| `inspect` | Examine a memory record, its decay state, and supersession chain. |
| `replay_episode` | Reconstruct a complete past session from a time anchor. |
| `conflict_resolve` | Run the [conflict resolution](../concepts/conflict-resolution.md) protocol. |
| `decision_log` | Query the `conflict_trace` — the audit log of resolved conflicts. |
| `analytics` | Run [analytics queries](./analytics.md) and get config suggestions. |

## Tool surface at a glance

```text
remember · recall · recall_or_gap · update · forget · reflect
inspect · replay_episode · conflict_resolve · decision_log · analytics
```

Each tool maps directly onto a method of the public `AgentMemory` API, so anything you
can do over MCP you can also do in-process from Rust or Node.
