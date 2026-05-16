# Agent-Memory Landing Page

## Hero Section

# Memory infrastructure for autonomous AI agents

Agent-Memory gives AI agents persistent, searchable, and context-aware memory so they can remember users, projects, decisions, workflows, and outcomes across sessions.

Build agents that do not start from zero every time.

**Primary CTA:** Get Started  
**Secondary CTA:** View GitHub

---

## Problem

Most AI agents are stateless. They can respond to a prompt, but they struggle to remember what happened before, why a decision was made, what a user prefers, or how a project has evolved.

That creates agents that feel disconnected, repetitive, and unreliable.

Agent-Memory solves this by giving agents a dedicated memory layer.

---

## What Agent-Memory Does

Agent-Memory helps autonomous agents store, retrieve, summarize, and reuse context.

It can remember:

- User preferences
- Project history
- Past conversations
- Tool execution results
- Product decisions
- Code review patterns
- Research findings
- Long-running workflow state

---

## Core Capabilities

### Persistent Memory

Store important context across sessions so agents can continue work without losing history.

### Semantic Search

Retrieve relevant memories using natural-language queries instead of rigid keyword matching.

### Project Context

Keep repository, product, customer, or workspace-specific knowledge available to agents.

### Session Memory

Track temporary state during active conversations, tasks, and workflows.

### Decision Memory

Capture decisions, rationales, and outcomes so future agents understand why something happened.

### Agent Runtime Integration

Designed to work with orchestration systems such as Platform-Agent, LangGraph, CrewAI, AutoGen, and custom agent runtimes.

---

## How It Works

```text
Agent receives a task
        ↓
Agent asks Agent-Memory for relevant context
        ↓
Agent-Memory retrieves memories and summaries
        ↓
Agent plans and executes the task
        ↓
Agent writes new observations back to memory
```

---

## Example: GitHub Code Review Agent

A code review agent can use Agent-Memory to remember:

- Repository architecture
- Coding standards
- Past review comments
- Known technical debt
- Team preferences
- Previous bug patterns

```text
Pull request opened
        ↓
Platform-Agent receives webhook
        ↓
Agent-Memory retrieves project context
        ↓
Agent reviews the diff
        ↓
Agent posts comments
        ↓
Agent-Memory stores review summary
```

---

## Built For

- AI agent platforms
- SaaS copilots
- Developer tools
- Product management agents
- Research agents
- Customer support agents
- Workflow automation systems
- Multi-agent applications

---

## Why Agent-Memory

### Modular

Use Agent-Memory as a standalone memory layer or connect it to your existing agent runtime.

### Agent-Native

Designed around agent workflows, not just chat history.

### Context-Aware

Supports user, project, session, tool, decision, and reflection memory.

### Extensible

Can evolve from local storage to semantic search, vector databases, multi-tenant APIs, and production observability.

---

## Suggested Memory Types

```text
session     Temporary memory for an active run
user        User preferences and recurring instructions
project     Repository, product, or workspace knowledge
tool        Tool calls, results, and execution history
decision    Important choices and rationales
reflection  Learnings, summaries, and improvement notes
```

---

## Developer API Preview

```python
memory.write(
    agent_id="code-review-agent",
    content="The team prefers small, focused PRs with explicit error handling.",
    metadata={"type": "project", "repo": "AGenNext/Agent-Memory"}
)

results = memory.search(
    agent_id="code-review-agent",
    query="What coding standards should I apply to this repository?",
    limit=5
)
```

---

## Platform-Agent Integration

Agent-Memory is designed to pair naturally with Platform-Agent.

```text
Platform-Agent = orchestration, planning, tool execution
Agent-Memory   = context, retrieval, persistence, learning
```

Together, they create a reusable foundation for production-grade autonomous agents.

---

## Roadmap

### Phase 1: Local Memory

- Basic memory client
- Local persistence
- Write and search operations
- Session summaries

### Phase 2: Semantic Retrieval

- Embedding support
- Vector search
- Metadata filters
- Memory ranking

### Phase 3: Agent Runtime Integration

- Platform-Agent adapter
- GitHub code review example
- Workflow memory hooks
- Tool execution history

### Phase 4: Production Platform

- API server
- Auth and tenants
- Observability
- Retention policies
- Import/export

---

## Final CTA

# Give your agents memory that compounds

Agent-Memory helps AI agents learn from context, remember what matters, and improve across workflows.

**Get Started**  
**View GitHub**
