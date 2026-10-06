# Memory model

Agent-Memory models memory as a cognitive process. This chapter covers the four
pillars of that model: **categories**, **decay**, **supersession**, and **epistemic
status**.

## Six categories

Every memory belongs to one of six categories, each with a different default decay
rate (λ).

| Category | λ (default) | Description |
|---|---|---|
| `episodic` | 0.000 | Raw conversation turns. **Immutable canonical truth.** Never decays. |
| `identity` | 0.001 | Who the person is, how they operate. Very slow decay. |
| `knowledge` | 0.020 | Learned facts. Decays without reinforcement. |
| `context` | 0.500 | Current session state. Fades in days. |
| `instruction` | 0.000 | Behavioural directives. Never decays. |
| `uncertainty` | 0.030 | Known unknowns emitted by the reconciler. |

## Ebbinghaus decay

Confidence decays exponentially with time since the memory was last reinforced:

```
effective_confidence = base_confidence × e^(−λ × days_since_reinforcement)
```

This is **computed at retrieval time, not stored**. Agent-Memory persists the base
confidence and the decay λ, then derives how much has decayed whenever you recall.

Every successful recall is a **reinforcement** — it resets the decay clock and nudges
confidence upward. Things that are useful stay accessible; things that are never used
fade. All weights are user-tunable via [`config/default.toml`](../reference/configuration.md).

## Supersede-not-overwrite

Memory records are **never overwritten**. Updates create a new version with
`derived_from` pointing to the old record. The supersession chain is always queryable —
you can always ask *what did the agent believe at time T?*

Episodic records (raw turns) **cannot be superseded by any means**. They are the
canonical record, and they are what the agent falls back to during
[conflict resolution](./conflict-resolution.md).

## Five epistemic statuses

`fact` · `belief` · `assumption` · `hearsay` · `inferred`

The agent distinguishes what it *knows* from what it *believes*. **Facts never decay
regardless of category** — knowing your name is not the same kind of memory as believing
the meeting is on Thursday. Treating them the same produces an agent that presents
hearsay with the same confidence as fact.
