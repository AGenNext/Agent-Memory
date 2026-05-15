# 🎯 Agent Samples

Ready-to-use AI agents with SurrealDB.

Based on SurrealDB tutorials: https://surrealdb.com/docs/explore/tutorials/tutorials/overview

---

## Quick Start

```bash
# 1. Start SurrealDB
docker run -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root memory

# 2. Run a sample
python samples/agents.py

# 3. Choose an agent (1-5)
```

---

## Files

| File | Description |
|------|-------------|
| **agent_template.py** | ✨ Build your own agent! |
| **agents.py** | 5 demo agents |
| **blueprints.py** | Code templates |

---

## 5 Demo Agents

### 1. Graph RAG Agent
```python
# Graph-enhanced retrieval
# Retrieves from both documents AND knowledge graph
```
**Tutorial:** https://surrealdb.com/docs/explore/tutorials/tutorials/build-a-genai-chatbot-with-graph-rag

### 2. Knowledge Graph Agent
```python
# Entity relationships
# Create entities and relate them
```
**Tutorial:** https://surrealdb.com/docs/explore/tutorials/tutorials/build-a-knowledge-graph-for-ai

### 3. AI Agent w/ Tools
```python
# Tool-calling agent
# Select and execute tools
```
**Tutorial:** https://surrealdb.com/docs/explore/tutorials/tutorials/build-an-ai-agent-with-python

### 4. Presence Agent
```python
# Real-time presence
# Track who's online in which room
```
**Tutorial:** https://surrealdb.com/docs/explore/tutorials/tutorials/build-a-realtime-presence-app

### 5. LangChain Agent
```python
# LangChain integration
# Vector store for RAG
```
**Tutorial:** https://surrealdb.com/docs/explore/tutorials/tutorials/build-a-minimal-langchain-chatbot

---

## Build Your Own Agent

```bash
# 1. Copy the template
cp samples/agent_template.py my_agent.py

# 2. Edit it
# - Change AGENT_NAME, DESCRIPTION
# - Override setup() for schema
# - Override train() for data
# - Override query() for logic

# 3. Run
python my_agent.py
```

### Template API

```python
class MyAgent(AgentTemplate):
    AGENT_NAME = "my-agent"
    
    async def setup(self):
        """Define schema"""
        await self.db.query("DEFINE TABLE ...")
    
    async def train(self):
        """Add training data"""
        await self.db.query("CREATE entity ...")
    
    async def query(self, question: str) -> dict:
        """Process query"""
        return {"answer": "...", "sources": [...]}
```

---

## Environment Variables

```bash
export DB_URL="ws://localhost:8000/rpc"
export DB_NS="memory"
export DB_DB="agent"
export DB_USER="root"
export DB_PASS="root"
export OPENAI_API_KEY="sk-..."
```

---

## Tutorials Reference

| Tutorial | Agent Type |
|----------|-----------|
| Graph RAG Chatbot | RAG + Graph |
| Knowledge Graph | Entity/Relations |
| AI Agent + Python | Tool calling |
| Realtime Presence | Live queries |
| LangChain Chatbot | Vector store |