#!/usr/bin/env python3
"""
Component: AI Agent

AI agent component with SurrealDB.
Based on: https://surrealdb.com/solutions (AI Agents use case)
"""

import asyncio
from surrealdb import Surreal


class AIAgent:
    """AI Agent component with SurrealDB memory."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc", 
                 agent_id: str = None, llm_provider: str = "openai"):
        self.url = url
        self.agent_id = agent_id
        self.llm_provider = llm_provider
        self.db = None
        self.system_prompt = "You are a helpful AI assistant."
    
    async def connect(self):
        """Connect to database."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "memory", "database": "agent"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Create agent schema."""
        schemas = [
            """
            DEFINE TABLE session SCHEMAFULL;
            DEFINE FIELD agent_id ON session TYPE string;
            DEFINE FIELD created ON session TYPE datetime DEFAULT time::now();
            DEFINE FIELD active ON session TYPE bool DEFAULT true;
            """,
            """
            DEFINE TABLE message SCHEMAFULL;
            DEFINE FIELD session ON message TYPE record(session);
            DEFINE FIELD role ON message TYPE string; -- system, user, assistant
            DEFINE FIELD content ON message TYPE string;
            DEFINE FIELD timestamp ON message TYPE datetime DEFAULT time::now();
            """,
            """
            DEFINE TABLE tool_call SCHEMAFULL;
            DEFINE FIELD session ON tool_call TYPE record(session);
            DEFINE FIELD tool ON tool_call TYPE string;
            DEFINE FIELD args ON tool_call TYPE object;
            DEFINE FIELD result ON tool_call TYPE object;
            """,
            """
            DEFINE TABLE context SCHEMAFULL;
            DEFINE FIELD entity ON context TYPE string;
            DEFINE FIELD type ON context TYPE string; -- user, file, api, document
            DEFINE FIELD content ON context TYPE string;
            DEFINE FIELD embedding ON context TYPE array<float>;
            DEFINE FIELD importance ON context TYPE float DEFAULT 0.5;
            DEFINE FIELD last_accessed ON context TYPE datetime;
            """,
        ]
        
        for schema in schemas:
            await self.db.query(schema)
        
        print("✅ AI Agent schema created")
    
    # ----- Session Management -----
    
    async def create_session(self, agent_id: str = None) -> dict:
        """Create new session."""
        agent_id = agent_id or f"agent_{id(self)}"
        result = await self.db.query(
            "CREATE session SET agent_id=$agent_id",
            {"agent_id": agent_id}
        )
        self.session_id = result[0][0]["id"]
        return result[0][0]
    
    async def get_or_create_session(self, agent_id: str) -> dict:
        """Get active session or create new."""
        result = await self.db.query(
            "SELECT * FROM session WHERE agent_id = $agent_id AND active = true ORDER BY created DESC LIMIT 1",
            {"agent_id": agent_id}
        )
        
        if result and result[0]:
            self.session_id = result[0][0]["id"]
            return result[0][0]
        
        return await self.create_session(agent_id)
    
    # ----- Message History -----
    
    async def add_message(self, role: str, content: str):
        """Add message to history."""
        result = await self.db.query(
            """CREATE message SET session=$session, role=$role, content=$content""",
            {"session": self.session_id, "role": role, "content": content}
        )
        return result[0][0]
    
    async def get_history(self, limit: int = 20) -> list:
        """Get message history."""
        result = await self.db.query(
            """SELECT * FROM message WHERE session = $session 
            ORDER BY timestamp DESC LIMIT $limit""",
            {"session": self.session_id, "limit": limit}
        )
        return result[0] if result else []
    
    # ----- Context / Memory -----
    
    async def store_context(self, entity: str, context_type: str, 
                          content: str, importance: float = 0.5):
        """Store context for retrieval."""
        result = await self.db.query(
            """CREATE context SET entity=$entity, type=$type, 
            content=$content, importance=$importance, last_accessed=time::now()""",
            {"entity": entity, "type": context_type, 
             "content": content, "importance": importance}
        )
        return result[0][0]
    
    async def retrieve_context(self, query: str, limit: int = 5) -> list:
        """Retrieve relevant context."""
        # Simple text search (would use vector in production)
        result = await self.db.query(
            """SELECT * FROM context WHERE content @@ $query 
            ORDER BY importance DESC LIMIT $limit""",
            {"query": query, "limit": limit}
        )
        
        # Update last_accessed
        if result and result[0]:
            for ctx in result[0]:
                await self.db.query(
                    "UPDATE context SET last_accessed=time::now() WHERE id = $id",
                    {"id": ctx["id"]}
                )
        
        return result[0] if result else []
    
    # ----- Tool Execution -----
    
    async def execute_tool(self, tool: str, args: dict) -> dict:
        """Execute tool and store result."""
        result = {"tool": tool, "args": args, "result": None}
        
        try:
            if tool == "query":
                result["result"] = await self.db.query(args["sql"], args.get("vars", {}))
            elif tool == "search":
                result["result"] = await self.retrieve_context(args["query"])
            else:
                result["error"] = f"Unknown tool: {tool}"
        except Exception as e:
            result["error"] = str(e)
        
        # Store tool call
        await self.db.query(
            """CREATE tool_call SET session=$session, tool=$tool, args=$args, result=$result""",
            {"session": self.session_id, "tool": tool, "args": args, "result": result}
        )
        
        return result
    
    # ----- Chat -----
    
    async def chat(self, user_message: str) -> str:
        """Process chat message."""
        # 1. Store user message
        await self.add_message("user", user_message)
        
        # 2. Retrieve relevant context
        contexts = await self.retrieve_context(user_message, limit=3)
        
        # 3. Build prompt
        history = await self.get_history(limit=10)
        context_text = "\n".join([f"- {c['content']}" for c in contexts])
        
        prompt = f"{self.system_prompt}\n\nContext:\n{context_text}\n\nHistory:\n"
        for msg in reversed(history):
            prompt += f"{msg['role']}: {msg['content']}\n"
        prompt += f"user: {user_message}\nassistant:"
        
        # 4. Get LLM response (placeholder)
        response = f"I understand: {user_message}"
        
        # 5. Store assistant response
        await self.add_message("assistant", response)
        
        return response
    
    # ----- Full Example -----
    
    async def run_example(self):
        """Run full example."""
        # Setup
        await self.setup_schema()
        
        # Create session
        session = await self.get_or_create_session("demo_agent")
        print(f"Session: {session['id']}")
        
        # Store some context
        await self.store_context("preferences", "user", "User prefers dark mode", 0.8)
        await self.store_context("project", "code", "Project is a SurrealDB demo", 0.9)
        
        # Chat
        response = await self.chat("What is my project about?")
        print(f"Response: {response}")
        
        # Get history
        history = await self.get_history()
        print(f"History: {len(history)} messages")


if __name__ == "__main__":
    async def main():
        agent = AIAgent()
        await agent.connect()
        await agent.run_example()
    
    asyncio.run(main())