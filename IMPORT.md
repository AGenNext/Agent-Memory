# Agent Blueprints - Importable via URL

Use these URLs in AI coding tools (Cursor, Windsurf, etc.) to import agents directly.

---

## Quick Import

Copy any URL below and use in your AI tool:

```
https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py
```

---

## Available Blueprints

### 1. Basic Agent Template
```
https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py
```
Simple template - override `setup()`, `train()`, `query()`

### 2. Graph RAG Agent
```
https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/rag_agent.py
```
Graph-enhanced RAG with knowledge graph context

### 3. Knowledge Graph Agent
```
https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/kg_agent.py
```
Entity relationships and traversal

### 4. Tool Calling Agent
```
https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/tool_agent.py
```
Agent with function tools

### 5. Presence Agent
```
https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/presence_agent.py
```
Real-time presence tracking

### 6. LangChain Agent
```
https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/langchain_agent.py
```
LangChain integration

---

## AI Tool Usage

### Cursor / Windsurf / Claude Code

```
@https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py

Create an agent that answers questions about Python
```

### Continue / VS Code

```python
# Import from URL
from samples.agent_template import AgentTemplate
```

---

## Prompt Examples

| Goal | Prompt |
|------|--------|
| Import template | `@agent_template.py create a FAQ bot` |
| Modify RAG | `@rag_agent.py add hybrid search` |
| Add tools | `@tool_agent.py add search tool` |
| Change schema | `@kg_agent.py add timestamps` |

---

## Files

All agent files in `samples/` directory:

- `agent_template.py` - Base template
- `rag_agent.py` - Graph RAG
- `kg_agent.py` - Knowledge Graph
- `tool_agent.py` - Tool calling
- `presence_agent.py` - Presence
- `langchain_agent.py` - LangChain