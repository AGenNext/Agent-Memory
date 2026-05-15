# Example: Create FAQ Agent from Template

## Original Template

From: `https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py`

```python
class AgentTemplate:
    async def setup(self):
        # Default schema
        pass
    
    async def query(self, question: str):
        return {"answer": "..."}
```

## Modified by AI

Prompt: "Create a FAQ bot that answers questions about SurrealDB"

```python
# Result (saved as faq_agent.py):

import asyncio
from agent_template import AgentTemplate

class FAQAgent(AgentTemplate):
    """FAQ Bot for SurrealDB"""
    
    AGENT_NAME = "surrealdb-faq"
    
    async def setup(self):
        """Setup FAQ schema"""
        await self.db.query("""
            DEFINE TABLE faq SCHEMAFULL;
            DEFINE FIELD question ON faq TYPE string;
            DEFINE FIELD answer ON faq TYPE string;
            DEFINE FIELD category ON faq TYPE string;
            DEFINE FIELD tags ON faq TYPE array<string>;
        """)
    
    async def query(self, question: str):
        """Find answer"""
        results = await self.db.query("""
            SELECT * FROM faq 
            WHERE question CONTAINS $q 
            LIMIT 1
        """, {"q": question})
        
        if results and results[0]:
            return {"answer": results[0][0]["answer"]}
        
        return {"answer": "I don't know the answer to that."}


if __name__ == "__main__":
    agent = FAQAgent()
    asyncio.run(agent.run())
```

---

## Create Your Own

### 1. Copy Template

```bash
curl -O https://raw.githubusercontent.com/AGenNext/Agent-Memory/main/samples/agent_template.py
```

### 2. Open in AI Tool

```
In Cursor/Windsurf:
@agent_template.py

Make a bot that tracks user conversations
```

### 3. AI Generates

```python
class ConversationAgent(AgentTemplate):
    """Tracks user conversations"""
    
    async def setup(self):
        await self.db.query("""
            DEFINE TABLE conversation SCHEMAFULL;
            DEFINE FIELD user_id ON conversation TYPE string;
            DEFINE FIELD messages ON conversation TYPE array;
        """)
    
    async def query(self, question):
        # Custom logic
        return {"answer": "..."}
```

### 4. Run

```bash
python conversation_agent.py
```

---

## Common Modifications

| Want to... | Override method |
|------------|-----------------|
| Custom schema | `setup()` |
| Custom data | `train()` |
| Custom logic | `query()` |
| Custom chat | `chat()` |

---

## Full Example Files

See `samples/` directory for working examples:

- `rag_agent.py` - Graph RAG
- `kg_agent.py` - Knowledge Graph
- `tool_agent.py` - Tool Calling
- `presence_agent.py` - Real-time
- `langchain_agent.py` - LangChain