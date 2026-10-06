# Conflict resolution

When what the agent recorded contradicts what a human says happened, it does not
immediately defer. It checks its recollection, considers the source, and sometimes
stands firm. The mechanism matters — and it is the most opinionated part of the system.

## The key insight

Schacter's research shows that **human confidence is not correlated with accuracy**.
People can be completely confident about things they got completely wrong. The most
reliable record of what was said is the written record — not what either party
remembers.

This is why agent memory systems that *always* defer to the human when challenged are
making an architectural mistake. The chat log is more reliable than human recall. An
agent that abandons what it recorded because a human expressed confidence is an agent
that will learn false things.

## Three conflict types

**Misinterpretation** — *"That's not what I meant"*
The agent stored an interpretation. The human corrects it. The agent accepts, versions
the interpretation, and preserves the original episodic turn.

**Agent stands firm** — *"You told me X"*
The human claims the agent said something different. The agent shows the exact episodic
record — verbatim, timestamped, session-linked. The chat log outranks human recall.
`AgentStandsFirm` is not stubbornness; it is epistemic hygiene. The agent offers a new
decision going forward — it does not revise history.

**Factual contradiction** — *"The number was different"*
The human disputes a number from the chat log. The agent shows the exact line, sets
`halt_reasoning = true`, and stops that reasoning thread from the contested value.

## The decision trace

Every conflict resolution is logged in `conflict_trace` with full calibration
reasoning. It is queryable via the [`decision_log`](../reference/mcp-tools.md) MCP tool,
so you can always audit *why* the agent resolved a conflict the way it did.
