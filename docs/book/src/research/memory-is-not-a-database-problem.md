# Memory is not a database problem

*Published by Autonomyx / AGenNext · May 2026*

---

Your AI agent forgets everything between sessions. You know this. The standard fix is to store conversation history in a vector database and retrieve relevant chunks at query time. It works well enough in demos. In production it breaks in ways that are hard to debug and harder to explain to users.

The problem is not the retrieval system. The problem is the mental model.

We have been treating agent memory as a database lookup problem. It is not. It is a cognitive problem. And the solutions look very different.

---

## What we got wrong

When you store memories in a vector database, you are making an implicit assumption: that all memories are equal, that they do not change over time, and that the job of memory is to retrieve what you stored.

Human memory makes none of these assumptions.

Human memory is reconstructive, not reproductive. When you recall something, you do not play back a recording. You reconstruct a plausible version of what happened, coloured by what you know now, what you were feeling then, and what has happened since. Daniel Schacter at Harvard has documented this exhaustively — memory is systematically biased toward what is familiar, what fits your current beliefs, and what you have thought about recently.

Human memory decays without use. Hermann Ebbinghaus showed in 1885 that retention follows an exponential curve: R = e^(−t/S). The rate of decay depends on how deeply something was encoded and how often it has been recalled since. Things you think about regularly stay sharp. Things you never revisit fade until they are gone.

Human memory distinguishes what you know from what you believe. You know your name. You believe the meeting is on Thursday. You assume the client liked the proposal. You heard from a colleague that the budget was cut. These are different epistemic states. Treating them the same produces an agent that presents hearsay with the same confidence as fact.

Human memory has a conflict resolution system. When what you remember contradicts what someone else says happened, you do not immediately defer. You check your recollection. You consider the source. You sometimes stand firm. You sometimes update. The mechanism matters.

And human memory has a gap protocol. When someone asks about something you cannot remember, you do not return an empty array. You try harder. You think about when it might have happened. You ask for a hint. If given a time anchor — "it was around the time of the project launch" — you can often reconstruct the whole context from that single cue.

None of this is in any vector database.

---

## What we built

Agent-Memory is our attempt to close this gap. It is an open source memory layer for AI agents built in Rust with embedded SurrealDB. Every design decision maps to a specific finding from cognitive science.

**Six memory categories with different decay rates.** Episodic memories — raw conversation turns — are immutable canonical truth. They never decay. Identity memories — who the person is, how they operate — decay very slowly. Knowledge decays at a medium rate without reinforcement. Context fades in days. Instructions never decay. The rates are configurable. They are Version 1 defaults. We do not claim they are optimal. We claim the model is correct.

**Ebbinghaus decay computed at retrieval time.** We do not store the effective confidence. We store the base confidence and the decay lambda, and compute how much has decayed since the memory was last reinforced. Every successful recall is a reinforcement — it resets the clock. Things that are useful stay accessible. Things that are never used fade.

**Five epistemic statuses.** Fact, belief, assumption, hearsay, inferred. Facts never decay regardless of category. The agent knows the difference between what it recorded as true and what it inferred as probable.

**Supersede-not-overwrite.** When a belief is updated, the old record is preserved with a timestamp and a pointer to the new one. The supersession chain is always queryable. You can always ask: what did the agent believe at time T? Episodic records cannot be superseded by any means. They are the canonical record.

**Five-tier escalating recall with a gap protocol.** Normal recall tries direct lookup and hybrid search. If the human insists something exists, we escalate through five tiers — including superseded memories, temporal windows, and scope relaxation — before admitting we cannot find it. When we cannot find it, we return a suggested prompt for the human. When the human provides a time anchor, we replay the complete session from that period into active context.

**Three-type conflict resolution.** Misinterpretation — the agent got the interpretation wrong, it accepts the correction and versions the interpretation. Agent stands firm — the human claims the agent said something different, the agent retrieves the exact episodic record and shows it verbatim. Factual contradiction — the human disputes a number from the chat log, the agent shows the exact line and halts reasoning from the contested value. Every conflict is logged with full calibration reasoning.

---

## The key insight

Schacter's research shows that human confidence is not correlated with accuracy. People can be completely confident about things they got completely wrong. The most reliable record of what was said is the written record — not what either party remembers.

This is why agent memory systems that defer to the human when challenged are making an architectural mistake. The chat log is more reliable than human recall. An agent that abandons what it recorded because a human expressed confidence is an agent that will learn false things.

The AgentStandsFirm conflict type is not stubbornness. It is epistemic hygiene. When the agent has a verbatim record with a timestamp and the human has a memory, the record wins. The agent offers a new decision going forward. It does not revise history.

---

## Forgetting is a feature

HSAM — Highly Superior Autobiographical Memory — is a rare condition in which people remember almost every day of their lives in vivid detail. It sounds like a superpower. People who have it describe it as a curse. Jill Price, one of the first people formally studied with HSAM, described it as being "haunted by the neverending stream of memory."

An agent that stored everything with equal fidelity would be the computational equivalent of HSAM. Every interaction, every incidental detail, every piece of context competing for attention with every important fact. The agent would surface irrelevant details with equal weight as critical ones.

The decay model is not a compromise. It is the correct design. Forgetting keeps the agent focused. What is important and reinforced survives. What is not relevant fades. The agent builds a mental model of where things live — a lattice of knowledge, in Farnam Street's framing — not a transcript of everything that was ever said.

---

## What we do not know

The decay lambdas we shipped are Version 1 defaults. They are empirically unvalidated. They depend on variables we cannot know theoretically — how frequently you interact with the agent, how much your context changes, what domain you are in, how long your sessions are.

Starting tomorrow we will publish real-world usage metrics from live deployments: decay tuning data, recall tier distribution, gap probe rates. These will be the signal needed to tune the weights empirically. The analytics tool in the library returns exact config changes to apply based on your retrieval traces.

There are no universally correct values. The architecture is correct. The weights are placeholders. Tune them with your own data.

---

## Try it

```bash
cargo add agent-memory
npm install @agentnxxt/agent-memory
```

The library embeds SurrealDB. No server. No install. No external dependency at runtime.

[github.com/AGenNext/Agent-Memory](https://github.com/AGenNext/Agent-Memory)

---

*Chinmay Panda is the founder of OpenAutonomyx and a contributor to the OpenID Foundation. This post describes Autonomyx original research on cognitive memory models applied to AI agent systems.*
