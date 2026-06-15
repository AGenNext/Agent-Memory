# Escalating recall

Human memory has a gap protocol. When someone asks about something you cannot
immediately recall, you do not return an empty array — you try harder, think about
*when* it might have happened, and ask for a hint. Agent-Memory does the same.

## The five tiers

When normal recall finds nothing and the human insists something exists, retrieval
escalates through five tiers before emitting a gap probe:

| Tier | Strategy |
|---|---|
| 1 | Direct lookup — category/scope filter, sub-ms |
| 2 | Hybrid BM25 + vector (HNSW) merged via Reciprocal Rank Fusion |
| 3 | Include superseded memories — maybe it was overwritten |
| 4 | Temporal expansion — search 7d, 30d, 90d, 365d windows by `known_time` |
| 5 | Scope relaxation — drop session and scope filters |
| → | Gap probe — returns `suggested_prompt` for the human |

## The gap probe

When all five tiers come up empty, the agent does not silently fail. It returns a
**gap probe** containing a `suggested_prompt` — a concrete question to ask the human
that would help locate the memory (often a request for a time anchor).

## Episodic replay

If the human provides a time anchor — *"it was around the time of the project launch"* —
`EpisodicReplay` loads the **complete session** from that period into active context.
Not just the fact, but everything that was happening at that time.

This mirrors how a single cue can reconstruct an entire remembered context in humans.
Because episodic records are [immutable and never superseded](./memory-model.md#supersede-not-overwrite),
the replayed session is the verbatim, canonical record of what actually happened.
