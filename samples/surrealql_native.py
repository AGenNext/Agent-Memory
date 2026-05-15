#!/usr/bin/env python3
"""
SURREALDB NATIVE Agent Tools

Using SurrealQL directly - no abstractions.
Reference: https://surrealdb.com/docs
"""

import asyncio
from surrealdb import Surreal


class SurrealQL:
    """Direct SurrealQL operations."""
    
    def __init__(self, url="ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def __aenter__(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "native", "database": "demo"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def __aexit__(self, *args):
        if self.db:
            await self.db.close()
    
    # ----- DEFINE -----
    
    async def define_table(self, table: str, schema: dict):
        """DEFINE TABLE with fields."""
        # Build fields
        for field, ftype in schema.items():
            await self.db.query(f"DEFINE FIELD {field} ON {table} TYPE {ftype};")
        await self.db.query(f"DEFINE TABLE {table} SCHEMAFULL;")
    
    async def define_index(self, table: str, field: str, index_type: str, **opts):
        """DEFINE INDEX."""
        sql = f"DEFINE INDEX {table}_{field} ON {table} FIELDS {field} {index_type}"
        
        if index_type == "HNSW":
            sql += f" DIMENSION {opts.get('dimension', 384)} DISTANCE {opts.get('distance', 'COSINE')}"
        elif index_type == "SEARCH":
            sql += f" ANALYZER {opts.get('analyzer', 'basic')} BM25"
        
        await self.db.query(sql)
    
    async def define_event(self, table: str, event: str, action: str):
        """DEFINE EVENT."""
        await self.db.query(f"DEFINE EVENT ON {table} WHEN {event} THEN {action};")
    
    # ----- CRUD -----
    
    async def create(self, table: str, data: dict):
        """CREATE record."""
        return await self.db.query(f"CREATE {table} SET $data", {"data": data})
    
    async def select(self, what: str, from_table: str, where: str = None, order: str = None, 
                limit: int = None):
        """SELECT records."""
        sql = f"SELECT {what} FROM {from_table}"
        
        if where:
            sql += f" WHERE {where}"
        if order:
            sql += f" ORDER BY {order}"
        if limit:
            sql += f" LIMIT {limit}"
        
        return await self.db.query(sql)
    
    async def update(self, table: str, where: str, data: dict):
        """UPDATE records."""
        return await self.db.query(
            f"UPDATE {table} SET $data WHERE {where}",
            {"data": data}
        )
    
    async def delete(self, table: str, where: str = None):
        """DELETE records."""
        sql = f"DELETE FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return await self.db.query(sql)
    
    # ----- RELATE -----
    
    async def relate(self, from_id: str, rel: str, to_id: str, data: dict = None):
        """RELATE records."""
        sql = f"RELATE {from_id} -> {rel} -> {to_id}"
        if data:
            sql += " SET $data"
            return await self.db.query(sql, {"data": data})
        return await self.db.query(sql)
    
    # ----- LIVE -----
    
    async def live(self, table: str, where: str = None):
        """LIVE SELECT - returns query for subscriptions."""
        sql = f"LIVE SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return sql
    
    # ----- Functions -----
    
    async def math(self, fn: str, *args):
        """Math functions."""
        return await self.db.query(f"RETURN math::{fn}({args})")
    
    async def string(self, fn: str, *args):
        """String functions."""
        return await self.db.query(f"RETURN string::{fn}({args})")
    
    async def time(self, fn: str, *args):
        """Time functions."""
        return await self.db.query(f"RETURN time::{fn}({args})")
    
    async def vector(self, fn: str, *args):
        """Vector functions."""
        return await self.db.query(f"RETURN vector::{fn}({args})")
    
    # ----- Raw Query -----
    
    async def query(self, sql: str, vars: dict = None):
        """Execute raw SurrealQL."""
        return await self.db.query(sql, vars or {})


# ----- Native Agent Example -----

async def agent_example():
    """Complete agent example using SurrealQL natively."""
    
    async with SurrealQL() as db:
        # 1. DEFINE schema
        print("📋 DEFINE schema...")
        
        await db.db.query("""
            DEFINE TABLE agent SCHEMAFULL;
            DEFINE FIELD name ON agent TYPE string;
            DEFINE FIELD role ON agent TYPE string;
            DEFINE FIELD context ON agent TYPE array<object>;
            DEFINE FIELD embedding ON agent TYPE array<float>;
        """)
        
        await db.db.query("""
            DEFINE TABLE message SCHEMAFULL;
            DEFINE FIELD agent ON message TYPE record(agent);
            DEFINE FIELD role ON message TYPE string;
            DEFINE FIELD content ON message TYPE string;
            DEFINE FIELD timestamp ON message TYPE datetime DEFAULT time::now();
        """)
        
        # 2. CREATE agents
        print("\n🤖 CREATE agents...")
        
        await db.create("agent", {
            "name": "Assistant",
            "role": "helper",
            "context": [],
        })
        
        await db.create("agent", {
            "name": "Researcher", 
            "role": "research",
            "context": [],
        })
        
        # 3. CREATE messages
        print("\n💬 CREATE messages...")
        
        await db.create("message", {
            "agent": "agent:assistant",
            "role": "assistant",
            "content": "Hello! How can I help?",
        })
        
        # 4. SELECT with relations
        print("\n🔍 SELECT with relations...")
        
        messages = await db.select(
            "*, agent.name AS agent_name",
            "message",
            where="role = 'assistant'",
            order="timestamp DESC",
            limit=10
        )
        print(f"   Found {len(messages[0])} messages")
        
        # 5. RELATE - create edges
        print("\n🔗 RELATE...")
        
        await db.relate("agent:assistant", "knows", "agent:research", {
            "strength": 0.8,
        })
        
        # 6. Vector search with functions
        print("\n📊 Vector functions...")
        
        cosine = await db.vector("distance::cosine", 
            [0.1, 0.2, 0.3], 
            [0.1, 0.2, 0.3]
        )
        print(f"   Cosine distance: {cosine}")
        
        # 7. LIVE query
        print("\n📡 LIVE query...")
        
        live_sql = await db.live("message")
        print(f"   {live_sql}")
        
        # 8. Events
        print("\n⚡ DEFINE EVENT...")
        
        await db.define_event(
            "message", 
            "CREATE",
            "RETURN 'New message: ' + this.content"
        )
        
        print("\n✅ SurrealDB native example complete!")


if __name__ == "__main__":
    asyncio.run(agent_example())