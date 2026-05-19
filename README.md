# Agent-Memory

Production memory SDK and contracts for AGenNext.

Agent-Memory owns durable agent memory, graph memory, vector memory, GraphRAG contracts, and decision/audit trace storage.

## Scope

Agent-Memory owns:

- memory contracts
- SurrealDB memory backend
- graph memory
- vector memory
- GraphRAG memory
- decision traces
- runtime memory APIs
- SurrealDB schemas

Agent-Memory does not own:

- sample agents
- framework comparisons
- runtime execution
- LangGraph adapters
- UI
- provider adapters

## Default backend

SurrealDB is the default backend.

```txt
Agent-Runtime / Agent-Chat / Agent-Dashboard
  ↓
Agent-Memory SDK
  ↓
SurrealDB
```

## Core rule

SurrealDB is the durable source of truth for memory, graph, vector retrieval, traces, and runtime state that belongs to memory.
