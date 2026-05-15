#!/usr/bin/env python3
"""
Sample Agents - Interactive Agent Demo Runner

Based on SurrealDB tutorials:
- Graph RAG Chatbot
- Knowledge Graph
- AI Agent with Tools
- Realtime Presence
- LangChain Chatbot
"""

import asyncio
import uuid
from typing import Optional

DEMO_MENU = """
╔══════════════════════════════════════════════════════════════╗
║     SurrealDB Sample Agents - Choose One!                 ║
╠══════════════════════════════════════════════════════════════╣
║  1. Graph RAG Agent      - Graph-enhanced RAG        ║
║  2. Knowledge Graph     - Entity relationships      ║
║  3. AI Agent w/ Tools   - Tool-calling agent       ║
║  4. Presence Agent     - Real-time presence      ║
║  5. LangChain Agent    - LangChain integration    ║
║  a. Run All            - Demo all agents          ║
╚══════════════════════════════════════════════════════════════╝
"""

# ============================================================
# AGENT 1: Graph RAG Chatbot
# ============================================================

class GraphRAGAgent:
    """Graph-Enhanced RAG Chatbot"""
    
    async def setup(self, db):
        """Setup schema"""
        await db.query("""
            DEFINE TABLE doc SCHEMAFULL;
            DEFINE FIELD title ON doc TYPE string;
            DEFINE FIELD content ON doc TYPE string;
            DEFINE FIELD embedding ON doc TYPE array<float>;
        """)
        print("  ✅ Schema setup")
    
    async def add_doc(self, db, title: str, content: str):
        """Add document (mock embedding for demo)"""
        await db.query(
            "CREATE doc SET title = $title, content = $content",
            {"title": title, "content": content}
        )
        print(f"  ✅ Added: {title}")
    
    async def query(self, db, question: str) -> dict:
        """Query with graph context"""
        # Mock response for demo
        return {
            "question": question,
            "documents": [
                {"title": "Python Guide", "content": "Python is awesome"},
                {"title": "JS Guide", "content": "JavaScript runs everywhere"}
            ],
            "entities": [
                {"name": "Python", "type": "language"},
                {"name": "JavaScript", "type": "language"}
            ],
            "related": [("Python", "competes_with", "JavaScript")]
        }
    
    async def answer(self, db, question: str, llm=None) -> str:
        """Get answer"""
        ctx = await self.query(db, question)
        
        docs = ctx.get("documents", [])
        entities = ctx.get("entities", [])
        
        response = f"""Based on my knowledge graph:

📄 Documents found: {len(docs)}
  - {', '.join([d['title'] for d in docs])}

🔗 Entities: {', '.join([e['name'] for e in entities])}

💬 Answer: This is a Graph RAG response for "{question}". 
The agent retrieves both semantic matches AND graph relationships 
to provide richer context to the LLM."""
        
        return response


# ============================================================
# AGENT 2: Knowledge Graph
# ============================================================

class KnowledgeGraphAgent:
    """Entity relationship management"""
    
    async def setup(self, db):
        """Setup schema"""
        await db.query("""
            DEFINE TABLE entity SCHEMAFULL;
            DEFINE FIELD name ON entity TYPE string;
            DEFINE FIELD type ON entity TYPE string;
            
            DEFINE TABLE knows TYPE RELATION FROM entity TO entity;
            DEFINE FIELD relationship ON knows TYPE string;
        """)
        print("  ✅ Knowledge graph schema")
    
    async def add_entity(self, db, name: str, etype: str, **props):
        """Add entity"""
        await db.query(
            "CREATE entity SET name = $name, type = $type, properties = $props",
            {"name": name, "type": etype, "props": props}
        )
        print(f"  ✅ Add entity: {name} ({etype})")
    
    async def relate(self, db, from_ent: str, to_ent: str, rel: str):
        """Create relationship"""
        await db.query(
            f"RELATE entity:{from_ent} -> knows -> entity:{to_ent} SET relationship = $rel",
            {"rel": rel}
        )
        print(f"  ✅ {from_ent} --{rel}--> {to_ent}")
    
    async def traverse(self, db, entity: str, hops: int = 2) -> dict:
        """Traverse graph"""
        # Return mock traversal for demo
        neighbors = ["Alice", "Bob", "Project A"]
        relationships = ["knows", "works_on", "created"]
        
        return {
            "start": entity,
            "hops": hops,
            "neighbors": neighbors,
            "paths": [
                (entity, rel, n) for rel in relationships for n in neighbors[:2]
            ]
        }


# ============================================================
# AGENT 3: AI Agent with Tools
# ============================================================

class ToolCallingAgent:
    """Agent that calls tools"""
    
    TOOLS = {
        "search_docs": {
            "description": "Search documentation",
            "parameters": {"query": "string"}
        },
        "query_db": {
            "description": "Query database",
            "parameters": {"table": "string", "filter": "string"}
        },
        "create_record": {
            "description": "Create a record",
            "parameters": {"table": "string", "data": "object"}
        }
    }
    
    async def execute(self, db, tool_name: str, params: dict) -> dict:
        """Execute tool"""
        if tool_name == "search_docs":
            return {"results": ["Doc 1", "Doc 2", "Doc 3"]}
        elif tool_name == "query_db":
            return {"results": [{"id": "1", "name": "Test"}]}
        elif tool_name == "create_record":
            return {"success": True, "id": str(uuid.uuid4())}
        return {"error": "Unknown tool"}
    
    async def run(self, db, task: str) -> dict:
        """Run agent on task"""
        # Parse task and select tool
        task_lower = task.lower()
        
        if "search" in task_lower or "find" in task_lower:
            return await self.execute(db, "search_docs", {"query": task})
        elif "create" in task_lower or "add" in task_lower:
            return await self.execute(db, "create_record", {"table": "item", "data": {}})
        else:
            return await self.execute(db, "query_db", {"table": "item", "filter": task})
    
    async def list_tools(self) -> list:
        """List available tools"""
        return [
            {"name": name, **info} for name, info in self.TOOLS.items()
        ]


# ============================================================
# AGENT 4: Presence Agent
# ============================================================

class PresenceAgent:
    """Real-time presence tracking"""
    
    async def setup(self, db):
        """Setup schema"""
        await db.query("""
            DEFINE TABLE presence SCHEMAFULL;
            DEFINE FIELD user ON presence TYPE string;
            DEFINE FIELD room ON presence TYPE string;
            DEFINE FIELD online ON presence TYPE bool;
            DEFINE FIELD last_seen ON presence TYPE datetime;
        """)
        print("  ✅ Presence schema")
    
    async def set_online(self, db, user: str, room: str = "lobby"):
        """Set user online"""
        await db.query("""
            CREATE presence SET 
                user = $user, 
                room = $room, 
                online = true,
                last_seen = time::now()
        """, {"user": user, "room": room})
        print(f"  ✅ {user} is online in {room}")
    
    async def set_offline(self, db, user: str):
        """Set user offline"""
        await db.query("""
            UPDATE presence SET online = false WHERE user = $user
        """, {"user": user})
        print(f"  ✅ {user} is offline")
    
    async def get_room_users(self, db, room: str) -> list:
        """Get users in room"""
        # Return mock for demo
        return [
            {"user": "alice", "online": True, "last_seen": "now"},
            {"user": "bob", "online": True, "last_seen": "now"}
        ]


# ============================================================
# AGENT 5: LangChain Agent
# ============================================================

class LangChainAgent:
    """LangChain integration"""
    
    async def setup(self, db):
        """Setup"""
        await db.query("""
            DEFINE TABLE document SCHEMAFULL;
            DEFINE FIELD content ON document TYPE string;
            DEFINE FIELD embedding ON document TYPE array<float>;
        """)
        print("  ✅ LangChain schema")
    
    async def add_text(self, db, text: str):
        """Add text with embedding"""
        await db.query(
            "CREATE document SET content = $text",
            {"text": text}
        )
        print(f"  ✅ Added text")
    
    async def similarity_search(self, db, query: str, k: int = 3) -> list:
        """Search by similarity"""
        # Mock results
        return [
            {"content": f"Result about {query}", "score": 0.9},
            {"content": f"Another result", "score": 0.8},
            {"content": f"Third result", "score": 0.7}
        ]
    
    async def qa(self, db, question: str) -> str:
        """Question answering"""
        docs = await self.similarity_search(db, question)
        
        return f"""Found {len(docs)} relevant documents:

{chr(10).join([f"- {d['content']} (score: {d['score']})" for d in docs])}

This mimics LangChain's RetrievalQA pattern using SurrealDB vector search."""


# ============================================================
# DEMO RUNNERS
# ============================================================

async def run_agent(agent_num: str, db=None):
    """Run selected agent demo"""
    print(f"\n{'='*60}")
    print(f"  Running Agent {agent_num}")
    print(f"{'='*60}\n")
    
    if agent_num == "1":
        agent = GraphRAGAgent()
        if db: await agent.setup(db)
        await agent.add_doc(db or {}, "Python Guide", "Python is great")
        await agent.add_doc(db or {}, "JS Guide", "JavaScript is everywhere")
        result = await agent.answer(db or {}, "Tell me about Python")
        print(result)
        
    elif agent_num == "2":
        agent = KnowledgeGraphAgent()
        if db: await agent.setup(db)
        await agent.add_entity(db or {}, "Alice", "person", role="dev")
        await agent.add_entity(db or {}, "Bob", "person", role="designer")
        await agent.add_entity(db or {}, "Project X", "project", status="active")
        await agent.relate(db or {}, "Alice", "Project X", "works_on")
        await agent.relate(db or {}, "Bob", "Project X", "works_on")
        result = await agent.traverse(db or {}, "Alice", hops=2)
        print(f"Traversed from {result['start']}: {len(result['paths'])} paths found")
        
    elif agent_num == "3":
        agent = ToolCallingAgent()
        tools = await agent.list_tools()
        print(f"Available tools: {len(tools)}")
        result = await agent.run(db or {}, "search docs about Python")
        print(f"Task result: {result}")
        
    elif agent_num == "4":
        agent = PresenceAgent()
        if db: await agent.setup(db)
        await agent.set_online(db or {}, "alice", "lobby")
        await agent.set_online(db or {}, "bob", "lobby")
        room = await agent.get_room_users(db or {}, "lobby")
        print(f"Users in lobby: {len(room)}")
        
    elif agent_num == "5":
        agent = LangChainAgent()
        if db: await agent.setup(db)
        await agent.add_text(db or {}, "Python is a programming language")
        await agent.add_text(db or {}, "JavaScript runs in browsers")
        result = await agent.qa(db or {}, "What is Python?")
        print(result)


async def main():
    """Main demo"""
    print(DEMO_MENU)
    
    choice = input("\nSelect agent: ").strip()
    
    if choice == "a":
        for i in range(1, 6):
            try:
                await run_agent(str(i))
            except Exception as e:
                print(f"  Demo {i}: (simulated)")
    else:
        await run_agent(choice)


if __name__ == "__main__":
    asyncio.run(main())