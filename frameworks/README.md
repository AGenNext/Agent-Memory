# Agent Frameworks - Integrations

Based on: https://surrealdb.com/docs/build/ai-agents/ai-frameworks

## Supported Frameworks

### 1. Agno
```python
# Install
pip install agno

# Use with SurrealDB
from agno import Agent
from agno.storage import SurrealDBStorage

storage = SurrealDBStorage(
    db_url="ws://localhost:8000/rpc",
    namespace="memory",
    database="agent"
)

agent = Agent(storage=storage)
```

### 2. CAMEL
```python
# Install
pip install camel-ai

# Use with SurrealDB
from camel.stores import SurrealDBStore

store = SurrealDBStore("ws://localhost:8000/rpc")
```

### 3. CrewAI
```python
# Install  
pip install crewai

# Use with SurrealDB
from crewai import Agent
from crewai.storage import SurrealDBStorage

storage = SurrealDBStorage(connection="ws://localhost:8000/rpc")
```

### 4. Dagster
```python
# Install
pip install dagster

# Use with Dagster + SurrealDB
from dagster_dbt import dbt_resource
from surrealdb import Surreal
```

### 5. Google ADK
```python
# Install
pip install google-adk

# Use with SurrealDB
from google.adk import Agent
from google.adk.db import SurrealDB
```

### 6. LangChain
```python
# Install
pip install langchain langchain-community

# Use as vector store
from langchain_community.vectorstores import SurrealVectorStore

vs = SurrealVectorStore(
    connection="ws://localhost:8000/rpc",
    embedding_function=embeddings
)
```

### 7. LlamaIndex
```python
# Install
pip install llama-index

# Use as vector store
from llama_index.vector_stores import SurrealDBVectorStore

vs = SurrealDBVectorStore(
    url="ws://localhost:8000/rpc",
    namespace="memory",
    database="agent"
)
```

### 8. PydanticAI
```python
# Install
pip install pydantic-ai

# Use with SurrealDB
from pydantic_ai.models import OpenAI as PydanticOpenAI
from agent_memory import SurrealMemory

memory = SurrealMemory("ws://localhost:8000/rpc")
```

### 9. smolagents
```python
# Install
pip install smolagents

# Use with SurrealDB as storage
from smolagents import CodeAgent
from smolagents.storage import SurrealStorage
```

---

## Comparison Table

| Framework | SurrealDB Use | Complexity |
|-----------|-------------|------------|
| **LangChain** | Vector store | 🟢 Easy |
| **LlamaIndex** | Vector store | 🟢 Easy |
| **PydanticAI** | Agent memory | 🟢 Easy |
| **CrewAI** | Storage | 🟡 Medium |
| **Agno** | Agent storage | 🟡 Medium |
| **smolagents** | Storage | 🟡 Medium |
| **Google ADK** | DB | 🟠 Advanced |
| **Dagster** | Pipeline | 🟠 Advanced |

---

## Code Examples

### LangChain RAG
```python
from langchain_community.vectorstores import SurrealVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain.chains import RetrievalQA
from openai import ChatOpenAI

embeddings = OpenAIEmbeddings()
vs = SurrealVectorStore.from_texts(
    texts=["Doc 1", "Doc 2"],
    embedding=embeddings,
    connection="ws://localhost:8000/rpc"
)

qa = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(),
    chain_type="stuff",
    retriever=vs.as_retriever()
)

result = qa("Your question")
```

### PydanticAI Agent
```python
from pydantic_ai import Agent
from surrealdb import Surreal

class SurrealMemory:
    def __init__(self, db_url):
        self.db = Surreal(db_url)
    
    async def save(self, role, content):
        await self.db.query("CREATE message SET role=$, content=$", role, content)
    
    async def get_history(self, limit=10):
        # Get history
        ...

agent = Agent(model="gpt-4o")
memory = SurrealMemory("ws://localhost:8000/rpc")
```

---

## Links

- [SurrealDB AI Agents Docs](https://surrealdb.com/docs/build/ai-agents/ai-frameworks)
- [LangChain Integration](https://surrealdb.com/docs/build/ai-agents/langchain)
- [PydanticAI](https://ai.pydantic.dev)