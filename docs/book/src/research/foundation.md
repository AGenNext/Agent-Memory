# Research foundation

Agent-Memory is an [Autonomyx](https://openautonomyx.com) original research project. The
memory model is grounded in peer-reviewed cognitive science, not in software engineering
conventions.

| Source | Contribution to Agent-Memory |
|---|---|
| **Schacter, Harvard (2025)** — *How Memory Works (and Doesn't)* | Memory is reconstruction not replay. Confidence ≠ accuracy. Source misattribution is the core false-memory mechanism. Basis for the `AgentStandsFirm` conflict type. |
| **Schacter (2001)** — *Seven Sins of Memory* | Transience, misattribution, suggestibility, bias — each maps to a specific system behaviour. Forgetting as adaptive feature. |
| **QBI, University of Queensland** — *How Are Memories Formed?* | Synaptic plasticity: active connections strengthen, unused weaken. Basis for reinforcement-on-recall and Ebbinghaus λ. Sleep replay = CortexSynthesiser. |
| **Psychology Today** — *How Memory Works* | Reconsolidation: every retrieval makes memory temporarily rewritable. Basis for `reconsolidation_note` on retrieval traces. |
| **Scientific American** — *Elephants Never Forget* | Memory serves survival. Older memories with survival value are more durable. Basis for the `importance` field and selective storage. |
| **BBC Future / HSAM research** | Perfect memory is pathological. Forgetting is a feature. Basis for the principle: the agent should not store everything. |
| **Farnam Street** — *Mental Models* | Build a mental model of where things live, not a memorised transcript. Basis for the CortexSynthesiser knowledge brief as a map, not a transcript. |
| **Spectron (SurrealDB)** | 6 typed categories, tri-temporal clocks, provenance-as-data, supersede-not-overwrite, four-tier retrieval. |
| **A-Mem (paper)** | Memory evolution via event queue — EvolutionWorker. |
| **Spacebot Cortex** | Background-synthesised working memory layers — CortexSynthesiser. |

## The core design principle

> **Optimize for resemblance to real-world memory behaviour, not architectural purity.**

For the long-form argument behind this approach, read
[Memory is not a database problem](./memory-is-not-a-database-problem.md).
