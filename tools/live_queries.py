#!/usr/bin/env python3
"""
Tool: LIVE Queries

Subscribe to changes - no polling.
Reference: https://surrealdb.com/use-cases/real-time
"""

import asyncio
from surrealdb import Surreal
from typing import Callable, AsyncIterator


class LiveQueryTool:
    """LIVE query subscription tool."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
        self.subscriptions = {}
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "live", "database": "queries"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- Subscribe -----
    
    async def subscribe(self, query: str) -> str:
        """Execute LIVE query - returns subscription ID."""
        # Create live query
        result = await self.db.query(query)
        
        # Get live query ID from result
        if result and result[0]:
            return result[0][0].get("id") if result[0] else None
        return None
    
    async def watch_table(self, table: str, 
                      callback: Callable = None) -> AsyncIterator:
        """Watch all changes on a table."""
        query = f"LIVE SELECT * FROM {table}"
        
        async for change in self.db.live(query):
            if callback:
                await callback(change)
            yield change
    
    async def watch_record(self, table: str, record_id: str,
                        callback: Callable = None) -> AsyncIterator:
        """Watch specific record."""
        query = f"LIVE SELECT * FROM {table}:{record_id}"
        
        async for change in self.db.live(query):
            if callback:
                await callback(change)
            yield change
    
    async def watch_where(self, table: str, where: str,
                       callback: Callable = None) -> AsyncIterator:
        """Watch filtered results."""
        query = f"LIVE SELECT * FROM {table} WHERE {where}"
        
        async for change in self.db.live(query):
            if callback:
                await callback(change)
            yield change
    
    # ----- Common Patterns -----
    
    async def watch_chat_room(self, room_id: str) -> AsyncIterator:
        """Watch chat room messages."""
        query = f"LIVE SELECT * FROM message WHERE room = 'room:{room_id}'"
        
        async for change in self.db.live(query):
            yield change
    
    async def watch_user(self, user_id: str) -> AsyncIterator:
        """Watch user profile."""
        query = f"LIVE SELECT * FROM user:user_id'"
        
        async for change in self.db.live(query):
            yield change
    
    async def watch_inventory(self, user_id: str) -> AsyncIterator:
        """Watch user inventory."""
        query = f"LIVE SELECT * FROM inventory WHERE owner = 'user:{user_id}'"
        
        async for change in self.db.live(query):
            yield change
    
    async def watch_orders(self, status: str = None) -> AsyncIterator:
        """Watch orders."""
        if status:
            query = f"LIVE SELECT * FROM order WHERE status = '{status}'"
        else:
            query = "LIVE SELECT * FROM order"
        
        async for change in self.db.live(query):
            yield change
    
    # ----- Multi-Agent Coordination -----
    
    async def watch_shared_context(self, context_id: str) -> AsyncIterator:
        """Watch shared context for multi-agent."""
        query = f"LIVE SELECT * FROM context WHERE id = 'context:{context_id}'"
        
        async for change in self.db.live(query):
            yield change
    
    async def watch_findings(self, task_id: str) -> AsyncIterator:
        """Watch agent findings."""
        query = f"LIVE SELECT * FROM finding WHERE task = 'task:{task_id}'"
        
        async for change in self.db.live(query):
            yield change
    
    # ----- Helper -----
    
    def format_change(self, change: dict) -> str:
        """Format change for display."""
        action = change.get("action", "update")
        if action == "CREATE":
            return f"➕ Created: {change.get('id')}"
        elif action == "UPDATE":
            return f"✏️ Updated: {change.get('id')}"
        elif action == "DELETE":
            return f"🗑️ Deleted: {change.get('id')}"
        return f"📝 {change}"


# Example usage
async def on_change(change: dict):
    """Handle change."""
    print(f"Change detected: {change}")


async def demo():
    """Demo live queries."""
    live = LiveQueryTool()
    await live.connect()
    
    # Watch table (non-blocking in real use)
    print("LIVE query tool ready")
    print("""
Usage:
    async for change in live.watch_table("message"):
        print(change)
    
    async for change in live.watch_chat_room("general"):
        print(change["content"])
    """)


if __name__ == "__main__":
    asyncio.run(demo())