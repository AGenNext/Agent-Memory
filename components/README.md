# Real-World Application Components

Build complete apps by combining components.

## Based on SurrealDB Solutions

Reference: https://surrealdb.com/solutions

## Available Components

| Component | File | Description |
|-----------|------|-------------|
| **REST API** | `components/api_server.py` | HTTP endpoints |
| **Auth** | `components/auth.py` | JWT authentication |
| **Frontend** | `components/frontend.py` | React + Vite template |
| **Healthcare** | `components/healthcare.py` | Patient management |
| **AI Agent** | `components/ai_agent.py` | Agent with memory |
| **Gaming** | `components/gaming.py` | Agentic NPCs, leaderboards |
| **Knowledge Graph** | `components/knowledge_graph.py` | Entity relations |

## Solution Use Cases

### AI Agents
```python
# components/ai_agent.py
from components.ai_agent import AIAgent

agent = AIAgent()
await agent.connect()
await agent.run_example()
```

### Healthcare
```python
# components/healthcare.py
from components.healthcare import HealthcareDB

db = HealthcareDB()
await db.connect()
patient = await db.register_patient("John", "MRN-001", "1980-01-01")
```

### Gaming
```python
# components/gaming.py
from components.gaming import GamingDB

db = GamingDB()
await db.connect()
npc = await db.create_npc("Eldrin", "merchant", ["Welcome!"])
```

### Knowledge Graph
```python
# components/knowledge_graph.py
from components.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()
await kg.connect()
await kg.add_entity("Alice", "person")
await kg.relate("Alice", "SurrealDB", "works_at")
```

## Build Full Stack

### Combine Components

```python
# my_app.py
from components.api_server import SurrealDBServer
from components.ai_agent import AIAgent
from components.auth import Auth

# 1. Auth
auth = Auth()

# 2. Agent with memory
agent = AIAgent()
await agent.connect()

# 3. REST API
server = SurrealDBServer()
await server.start()
app = server.app()
```

### Full Stack Example

```python
# Start server
# $ python components/api_server.py

# API:
# POST /signin
# POST /sql
# GET /key/{table}
# POST /key/{table}
# GET /health
# GET /export
```

## Industry Solutions

| Industry | Component | Features |
|----------|-----------|----------|
| **Healthcare** | `healthcare.py` | Patients, vitals, alerts |
| **Finance** | - | (your component) |
| **Gaming** | `gaming.py` | NPCs, leaderboards |
| **Retail** | - | (your component) |
| **Defense** | - | (your component) |

## Templates

### Start a Project

```bash
# Create new component
cp components/api_server.py components/my_component.py

# Edit the schema and operations

# Import in your app
from components import my_component
```

## Add More Components

Create new components following the pattern:

```python
class MyComponent:
    def __init__(self, url="ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        # ... auth
        return self
    
    async def setup_schema(self):
        # DEFINE TABLE ...
        pass
    
    # Your methods
    async def my_operation(self):
        pass
```

## Resources

- [SurrealDB Solutions](https://surrealdb.com/solutions)
- [Use Cases](https://surrealdb.com/solutions#use-cases)
- [SDK Docs](https://surrealdb.com/docs/surrealql/sdk)