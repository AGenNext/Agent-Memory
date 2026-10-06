# Configuration

All decay weights, thresholds, and intervals are tunable via `config/default.toml`.

```toml
[decay.category]
identity    = 0.001   # very slow — name, role
knowledge   = 0.020   # medium — decays without use
episodic    = 0.100   # fast — raw conversation
context     = 0.500   # very fast — current session
instruction = 0.000   # never — behavioural directives

[retrieval]
threshold            = 0.15   # minimum confidence for normal recall
escalating_threshold = 0.05   # minimum for deep search

[reconciler]
confidence_floor       = 0.40  # below this → emit uncertainty instead of superseding
human_statement_trust  = 0.90  # direct human statement in current turn
```

## These are Version 1 defaults

The weights shipped here are **empirically unvalidated**. They depend on variables that
cannot be known theoretically — how frequently you interact with the agent, how much
your context changes, what domain you are in, how long your sessions are.

> There are no universally correct values. The architecture is correct. The weights are
> placeholders. Tune them with your own data.

The [analytics tool](./analytics.md) collects the signal needed to tune them and returns
exact `config.toml` changes to apply.
