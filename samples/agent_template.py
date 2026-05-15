#!/usr/bin/env python3
"""
🎯 Agent Blueprint Template

Copy this template to build your own SurrealDB-powered AI agent.

Usage:
    cp agent_template.py my_agent.py
    # Edit my_agent.py
    python my_agent.py
"""

import asyncio
import os
from datetime import datetime
from typing import Any

# ==============================================================================
# TEMPLATE: Edit these values
# ==============================================================================

AGENT_NAME = "my-agent"
AGENT_VERSION = "0.1.0"
DESCRIPTION = "Your agent description here"

# SurrealDB connection
DB_URL = os.getenv("DB_URL", "ws://localhost:8000/rpc")
DB_NS = os.getenv("DB_NS", "memory")
DB_DB = os.getenv("DB_DB", "agent")
DB_USER = os.getenv("DB_USER", "root")
DB_PASS = os.getenv("DB_PASS", "root")

# OpenAI (optional)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ==============================================================================
# CORE AGENT CLASS - Edit logic below
# ==============================================================================

class AgentTemplate:
    """
    Agent Blueprint - Extend this class to build your agent.
    
    Override these methods:
    - setup()      - Initialize schema
    - train()     - Add training data
    - query()     - Process and answer
    - chat()      - Interactive chat loop
    """
    
    def __init__(self, db_url: str = DB_URL):
        self.db_url = db_url
        self.db = None
        self.connected = False
    
    # -------------------------------------------------------------------------
    # CONNECTION
    # -------------------------------------------------------------------------
    
    async def connect(self):
        """Connect to SurrealDB"""
        from surrealdb import Surreal
        self.db = Surreal(self.db_url)
        await self.db.connect()
        await self.db.use({"namespace": DB_NS, "database": DB_DB})
        await self.db.signin({"username": DB_USER, "password": DB_PASS})
        self.connected = True
        print(f"✅ Connected to {self.db_url}")
    
    async def disconnect(self):
        """Disconnect"""
        if self.db:
            await self.db.close()
        self.connected = False
        print("👋 Disconnected")
    
    # -------------------------------------------------------------------------
    # SCHEMA - Override to customize
    # -------------------------------------------------------------------------
    
    async def setup(self):
        """
        Setup database schema.
        Override this method to define your tables and fields.
        """
        # Example: Create tables
        await self.db.query("""
            -- Sessions
            DEFINE TABLE session SCHEMAFULL;
            DEFINE FIELD user_id ON session TYPE string;
            DEFINE FIELD created ON session TYPE datetime DEFAULT time::now();
            
            -- Messages
            DEFINE TABLE message SCHEMAFULL;
            DEFINE FIELD session ON message TYPE record(session);
            DEFINE FIELD role ON message TYPE string;
            DEFINE FIELD content ON message TYPE string;
            
            -- Entities (knowledge graph)
            DEFINE TABLE entity SCHEMAFULL;
            DEFINE FIELD name ON entity TYPE string;
            DEFINE FIELD type ON entity TYPE string;
            DEFINE FIELD properties ON entity TYPE object;
        """)
        print("✅ Schema setup complete!")
    
    # -------------------------------------------------------------------------
    # TRAINING DATA - Override to customize
    # -------------------------------------------------------------------------
    
    async def train(self):
        """
        Add training/knowledge data.
        Override this method to load your data.
        """
        # Example: Add sample data
        await self.db.query("""
            CREATE entity SET 
                name = 'SurrealDB', 
                type = 'database',
                properties = {description: 'Multi-model database'}
        """)
        print("✅ Training data loaded!")
    
    # -------------------------------------------------------------------------
    # QUERY - Override to customize
    # -------------------------------------------------------------------------
    
    async def query(self, question: str) -> dict:
        """
        Process a query and return response.
        Override this method to implement your logic.
        
        Args:
            question: User's question
            
        Returns:
            dict with 'answer' and optional 'sources', 'context'
        """
        # Example implementation - modify this!
        
        # 1. Search knowledge base
        results = await self.db.query("""
            SELECT * FROM entity LIMIT 5
        """)
        
        # 2. Build answer
        entities = results[0] if results and results[0] else []
        
        answer = f"I found {len(entities)} related entities."
        
        return {
            "answer": answer,
            "sources": entities,
            "question": question,
            "timestamp": datetime.now().isoformat()
        }
    
    # -------------------------------------------------------------------------
    # CHAT - Override to customize
    # -------------------------------------------------------------------------
    
    async def chat(self, message: str, session_id: str = None) -> str:
        """
        Process chat message.
        Override to add conversation history, etc.
        """
        # Create session if not exists
        if not session_id:
            import uuid
            session_id = f"session:{uuid.uuid4().hex[:8]}"
            await self.db.query(f"""
                CREATE {session_id} SET user_id = 'anonymous', created = time::now()
            """)
        
        # Save messages
        await self.db.query("""
            CREATE message SET 
                session = $session,
                role = 'user',
                content = $content
        """, {"session": session_id, "content": message})
        
        # Get response
        result = await self.query(message)
        
        # Save assistant response
        await self.db.query("""
            CREATE message SET 
                session = $session,
                role = 'assistant',
                content = $content
        """, {"session": session_id, "content": result["answer"]})
        
        return result["answer"]
    
    # -------------------------------------------------------------------------
    # RUN - Main entry point
    # -------------------------------------------------------------------------
    
    async def run(self):
        """Main run loop"""
        # Connect
        if not self.connected:
            await self.connect()
        
        # Setup schema
        await self.setup()
        
        # Train
        await self.train()
        
        print(f"\n{'='*60}")
        print(f"🎯 {AGENT_NAME} v{AGENT_VERSION}")
        print(f"   {DESCRIPTION}")
        print(f"{'='*60}")
        print("\nType 'quit' to exit\n")
        
        session_id = None
        
        while True:
            message = input("You: ").strip()
            
            if message.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!")
                break
            
            if not message:
                continue
            
            try:
                response = await self.chat(message, session_id)
                print(f"\nBot: {response}\n")
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
        
        await self.disconnect()


# ==============================================================================
# EXAMPLE: Custom Agent (uncomment to use)
# ==============================================================================

"""
# Example: Custom Agent extending template
class MyCustomAgent(AgentTemplate):
    AGENT_NAME = "my-custom-agent"
    
    async def setup(self):
        # Custom schema
        await self.db.query("""
            DEFINE TABLE document SET content = 'hello world';
        """)
    
    async def query(self, question: str):
        # Custom logic
        return {
            "answer": f"This is my custom response to: {question}",
            "custom": True
        }
"""


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    agent = AgentTemplate()
    asyncio.run(agent.run())