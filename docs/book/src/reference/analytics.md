# Analytics

The analytics engine is a generic, registry-based telemetry layer. It analyses your
retrieval traces and returns **exact config changes to apply** — no code changes needed.

```rust
// Built-in queries — extensible registry, no code changes needed
memory.analytics("my-agent", "decay_tuning", 30).await?
// → gap probe rate, tier distribution, config_suggestions: {"decay.category.knowledge": "0.014"}

memory.analytics("my-agent", "summary", 30).await?
// → all analyses merged, highest severity first

memory.analytics("my-agent", "available", 30).await?
// → lists all registered query names
```

## config_suggestions

The key output is `config_suggestions` — exact `config.toml` changes derived from your
real retrieval behaviour. The human copies them into
[`config/default.toml`](./configuration.md), restarts, and the weights are tuned.

This is how the [empirically-unvalidated Version 1 defaults](./configuration.md) get
turned into values that fit *your* deployment: the architecture is fixed, the weights
are placeholders, and analytics produce the signal to tune them.
