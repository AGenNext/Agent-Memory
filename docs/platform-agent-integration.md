# Platform-Agent Integration

This document explains how `AGenNext/Agent-Memory` can support and integrate with the `openautonomyx/Platform-Agent` runtime.

## Purpose

`Agent-Memory` provides the memory layer for autonomous agents. `Platform-Agent` provides the orchestration/runtime layer that plans tasks, executes tools, manages workflows, and coordinates agent behavior.

Together, they form a reusable foundation for building production-grade autonomous AI agents.

```text
Platform-Agent
    ↓
Agent planner / executor / workflows
    ↓
Agent-Memory
    ↓
Short-term memory, long-term memory, semantic retrieval, user/project context
```

## Recommended Responsibility Split

### Platform-Agent

Platform-Agent should own:

- Agent lifecycle
- Task planning
- Tool execution
- Workflow routing
- Multi-agent coordination
- API/webhook entry points
- Observability hooks

### Agent-Memory

Agent-Memory should own:

- Short-term session memory
- Long-term agent memory
- Semantic search and retrieval
- Memory persistence
- Memory scoring and summarization
- User, project, and task context storage

## Integration Contract

Platform-Agent should interact with Agent-Memory through a simple memory interface.

```python
class AgentMemoryClient:
    def write_memory(self, agent_id: str, content: str, metadata: dict | None = None) -> str:
        """Persist a memory item and return its ID."""
        raise NotImplementedError

    def search_memory(self, agent_id: str, query: str, limit: int = 10) -> list[dict]:
        """Return relevant memories for an agent and query."""
        raise NotImplementedError

    def summarize_context(self, agent_id: str, session_id: str) -> str:
        """Return a compact context summary for the active agent session."""
        raise NotImplementedError
```

## Example Flow

```text
1. User asks Platform-Agent to perform a task.
2. Platform-Agent requests relevant memories from Agent-Memory.
3. Agent-Memory returns contextual facts, prior actions, and relevant project history.
4. Platform-Agent plans and executes the task.
5. Platform-Agent writes new observations, decisions, and outcomes back to Agent-Memory.
```

## Example Use Case: GitHub Code Review Agent

```text
Pull request opened
    ↓
Platform-Agent receives GitHub webhook
    ↓
Platform-Agent asks Agent-Memory for repo/project context
    ↓
Agent-Memory returns previous review patterns, coding standards, architecture notes
    ↓
Platform-Agent reviews the diff
    ↓
Platform-Agent posts PR comments
    ↓
Platform-Agent writes review summary back to Agent-Memory
```

## Suggested Memory Types

Agent-Memory should support these memory categories:

- `session`: Temporary memory for an active run or conversation
- `user`: User preferences, recurring instructions, and personal context
- `project`: Repository, product, or workspace-specific knowledge
- `tool`: Tool execution history and outcomes
- `decision`: Important decisions made by an agent
- `reflection`: Summaries, learnings, and improvement notes

## Minimal API Shape

A future HTTP interface could expose:

```http
POST /memory/write
POST /memory/search
POST /memory/summarize
GET /memory/{memory_id}
DELETE /memory/{memory_id}
```

## First MVP Goal

The first integration milestone should be:

> Platform-Agent can call Agent-Memory to retrieve project context before executing a GitHub code review workflow, then write the final review summary back into memory.

## Roadmap

### Phase 1: Local Memory Client

- Add Python client interface
- Store memories locally or in SQLite
- Support basic write/search/summarize operations

### Phase 2: Semantic Memory

- Add embeddings
- Add vector search
- Add metadata filters
- Add memory ranking

### Phase 3: Platform-Agent Runtime Integration

- Add Platform-Agent adapter
- Add code-review workflow example
- Add GitHub PR memory context retrieval
- Add review summary persistence

### Phase 4: Production Readiness

- Add auth
- Add multi-tenant isolation
- Add observability
- Add retention policies
- Add memory export/import

## Notes

This repo should remain focused on memory. Platform-Agent should depend on Agent-Memory, not the other way around. That keeps the architecture modular and reusable across different autonomous agent products.