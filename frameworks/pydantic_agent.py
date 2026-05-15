#!/usr/bin/env python3
"""
Framework: PydanticAI Agent with SurrealDB

A framework for building type-safe AI agents with SurrealDB memory.

Usage:
    from frameworks.pydantic_agent import Agent
    
    agent = Agent(
        model="openai:gpt-4o",
        system_prompt="You are a helpful assistant"
    )
    result = await agent.run("Hello")
"""

import asyncio
from datetime import datetime
from typing import Any, Optional
from pydantic_ai import Agent as PydanticAgent
from pydantic import BaseModel
from surrealdb import Surreal


class SurrealMemory:
    """Memory using SurrealDB"""
    
    def __init__(self, db_url: str = "ws://localhost:8000/rpc"):
        self.db_url = db_url
        self.db: Optional[Surreal] = None
    
    async def __aenter__(self):
        self.db = Surreal(self.db_url)
        await self.db.connect()
        await self.db.use({"namespace": "memory", "database": "agent"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def __aexit__(self, *args):
        if self.db:
            await self.db.close()
    
    async def add_message(self, role: str, content: str):
        """Add message to memory"""
        await self.db.query(
            "CREATE message SET role = $role, content = $content, created = time::now()",
            {"role": role, "content": content}
        )
    
    async def get_history(self, limit: int = 10):
        """Get conversation history"""
        result = await self.db.query(
            "SELECT * FROM message ORDER BY created DESC LIMIT $limit",
            {"limit": limit}
        )
        return result[0] if result and result[0] else []


class PydanticAIAgent:
    """
    PydanticAI Agent with SurrealDB memory.
    
    Example:
        agent = PydanticAIAgent(
            model="openai:gpt-4o",
            system_prompt="You are a helpful assistant"
        )
        
        async def main():
            async with agent.memory as mem:
                result = await agent.run("Hello")
    """
    
    def __init__(
        self,
        model: str = "openai:gpt-4o-mini",
        system_prompt: str = "You are a helpful AI assistant.",
        db_url: str = "ws://localhost:8000/rpc",
    ):
        self.model = model
        self.system_prompt = system_prompt
        self.db_url = db_url
        self._agent = PydanticAgent(model)
        self.memory = SurrealMemory(db_url)
    
    async def run(self, user_message: str) -> str:
        """Run agent with memory"""
        async with self.memory as mem:
            # Get history
            history = await mem.get_history()
            
            # Build messages
            messages = [{"role": "system", "content": self.system_prompt}]
            for msg in reversed(history):
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            messages.append({"role": "user", "content": user_message})
            
            # Run
            result = await self._agent.run(user_message)
            
            # Save to memory
            await mem.add_message("user", user_message)
            await mem.add_message("assistant", str(result))
            
            return str(result)


# Example usage
if __name__ == "__main__":
    async def main():
        agent = PydanticAIAgent(
            model="openai:gpt-4o-mini",
            system_prompt="You are a Python expert."
        )
        
        result = await agent.run("How do I create a class?")
        print(f"Agent: {result}")
    
    asyncio.run(main())