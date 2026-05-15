#!/usr/bin/env python3
"""
Plugin: Real-Time Live Queries

Real-time live queries for SurrealDB.
Based on: https://surrealdb.com/use-cases/real-time
"""

import asyncio
from surrealdb import Surreal


class RealTimePlugin:
    """Real-time live query plugin."""
    
    PLUGIN_NAME = "realtime"
    PLUGIN_VERSION = "1.0.0"
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def install(self):
        """Install plugin."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "realtime", "database": "live"})
        await self.db.signin({"username": "root", "password": "root"})
        
        # Live query tracking
        await self.db.query("""
            DEFINE TABLE _live_subscription SCHEMAFULL;
            DEFINE FIELD query ON _live_subscription TYPE string;
            DEFINE FIELD table ON _live_subscription TYPE string;
            DEFINE FIELD active ON _live_subscription TYPE bool DEFAULT true;
            DEFINE FIELD callback ON _live_subscription TYPE string;
        """)
        
        print(f"✅ Real-time plugin installed")
        return self
    
    # ----- Live Query -----
    
    async def subscribe(self, query: str, callback=None):
        """Subscribe to live query changes."""
        # Execute live query
        async with self.db.live(query) as live:
            self._live = live
            
            # Listen for changes
            async for change in live:
                print(f"Change: {change}")
                if callback:
                    await callback(change)
                
                # Store in tracking
                await self.db.query(
                    """CREATE _live_subscription SET query=$q""",
                    {"q": query}
                )
    
    async def subscribe_table(self, table: str, callback=None):
        """Subscribe to table changes."""
        await self.subscribe(f"LIVE SELECT * FROM {table}", callback)
    
    async def subscribe_record(self, table: str, record_id: str, callback=None):
        """Subscribe to specific record."""
        await self.subscribe(f"LIVE SELECT * FROM {table}:{record_id}", callback)
    
    # ----- WebSocket Streaming -----
    
    async def stream_changes(self, table: str):
        """Stream changes from table via WebSocket."""
        query = f"LIVE SELECT * FROM {table}"
        
        # This would be used with actual WebSocket
        return query
    
    # ----- Events -----
    
    async def create_event(self, event_type: str, table: str, 
                       action: str, handler: str):
        """Create database event trigger."""
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN {action} THEN
                RETURN '{event_type}';
        """)
        
        print(f"✅ Event created: {event_type} on {table}")
    
    async def create_audit_log(self, table: str):
        """Create audit log for table."""
        await self.db.query(f"""
            DEFINE TABLE _{table}_audit SCHEMAFULL;
            DEFINE FIELD record ON _{table}_audit TYPE record({table});
            DEFINE FIELD action ON _{table}_audit TYPE string;
            DEFINE FIELD timestamp ON _{table}_audit TYPE datetime DEFAULT time::now();
            DEFINE FIELD user ON _{table}_audit TYPE string;
        """)
        
        # Create trigger
        await self.db.query(f"""
            DEFINE EVENT ON {table} WHEN CREATE THEN
                CREATE _{table}_audit SET record = this.id, action = 'create';
        """)
        
        print(f"✅ Audit log created for {table}")
    
    # ----- Collaborative -----
    
    async def watch(self, table: str, record_id: str = None) -> dict:
        """Watch record for changes."""
        if record_id:
            query = f"LIVE SELECT * FROM {table}:{record_id}"
        else:
            query = f"LIVE SELECT * FROM {table}"
        
        return {"query": query, "watching": True}
    
    async def broadcast(self, channel: str, message: dict):
        """Broadcast to channel (simulated)."""
        # Store in broadcast table
        result = await self.db.query(
            "CREATE broadcast SET channel=$ch, message=$msg, time=time::now()",
            {"ch": channel, "msg": message}
        )


async def demo():
    """Demo."""
    plugin = RealTimePlugin()
    await plugin.install()
    
    # Create audit log
    await plugin.create_audit_log("user")
    
    # Watch for changes
    query = await plugin.watch("chat_message", "room:general")
    print(f"Subscribed: {query}")


if __name__ == "__main__":
    asyncio.run(demo())