# Quick start

The library boots an embedded SurrealDB instance in-process — no server, no install.

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

## What just happened

1. **`open`** boots the embedded store and lazily creates the schema on first use.
2. **`remember`** stores a memory in the `identity` category. Because identity decays
   very slowly (λ = 0.001), this preference will stay accessible for a long time even
   if it is never recalled again. See the [memory model](../concepts/memory-model.md).
3. **`recall_or_gap`** runs normal recall, and — if the human insists something exists —
   escalates through [five retrieval tiers](../concepts/escalating-recall.md) before
   admitting it cannot find the memory and returning a `suggested_prompt`.

## Next steps

- Understand how memories decay and supersede each other → [Memory model](../concepts/memory-model.md)
- Learn how recall escalates and replays episodes → [Escalating recall](../concepts/escalating-recall.md)
- Tune decay weights and thresholds → [Configuration](../reference/configuration.md)
