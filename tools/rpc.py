#!/usr/bin/env python3
"""
Tool: RPC Remote Procedure Calls

Execute functions on the database server.
Reference: SurrealDB RPC
"""

import asyncio
from surrealdb import Surreal


class RPCTool:
    """RPC tool for SurrealDB."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "rpc", "database": "calls"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- Query -----
    
    async def query(self, sql: str, vars: dict = None) -> list:
        """Execute SurrealQL query."""
        result = await self.db.query(sql, vars or {})
        return result[0] if result else []
    
    # ----- CRUD -----
    
    async def create(self, table: str, data: dict) -> dict:
        """Create record."""
        result = await self.db.query(
            f"CREATE {table} SET $data",
            {"data": data}
        )
        return result[0][0] if result else None
    
    async def select(self, table: str) -> list:
        """Select all."""
        result = await self.db.query(f"SELECT * FROM {table}")
        return result[0] if result else []
    
    async def select_one(self, table: str, record_id: str) -> dict:
        """Select one."""
        result = await self.db.query(f"SELECT * FROM {table}:{record_id}")
        return result[0][0] if result and result[0] else None
    
    async def update(self, table: str, record_id: str, data: dict) -> dict:
        """Update record."""
        result = await self.db.query(
            f"UPDATE {table}:{record_id} SET $data",
            {"data": data}
        )
        return result[0][0] if result else None
    
    async def delete(self, table: str, record_id: str) -> dict:
        """Delete record."""
        result = await self.db.query(f"DELETE FROM {table}:{record_id}")
        return {"deleted": True}
    
    # ----- Graph -----
    
    async def relate(self, from_id: str, to_id: str, relation: str, data: dict = None) -> dict:
        """Create relation."""
        sql = f"RELATE {from_id} -> {relation} -> {to_id}"
        if data:
            sql += f" SET $data"
        
        result = await self.db.query(sql, {"data": data or {}})
        return result[0][0] if result else None
    
    async def get_relations(self, from_id: str, relation: str) -> list:
        """Get outgoing relations."""
        result = await self.db.query(
            f"SELECT * FROM {from_id}->{relation}->entity"
        )
        return result[0] if result else []
    
    async def get_incoming(self, to_id: str, relation: str) -> list:
        """Get incoming relations."""
        result = await self.db.query(
            f"SELECT * FROM entity<-{relation}<-{to_id}"
        )
        return result[0] if result else []
    
    # ----- Functions -----
    
    async def call_function(self, name: str, *args) -> any:
        """Call database function."""
        args_str = ", ".join([f"$arg{i}" for i in range(len(args))])
        vars_dict = {f"arg{i}": arg for i, arg in enumerate(args)}
        
        result = await self.db.query(
            f"RETURN {name}({args_str})",
            vars_dict
        )
        return result[0][0] if result else None
    
    # ----- Batch -----
    
    async def batch(self, operations: list) -> list:
        """Execute batch operations."""
        results = []
        for op in operations:
            if op["type"] == "create":
                result = await self.create(op["table"], op["data"])
            elif op["type"] == "update":
                result = await self.update(op["table"], op["id"], op["data"])
            elif op["type"] == "delete":
                result = await self.delete(op["table"], op["id"])
            else:
                result = await self.query(op["sql"], op.get("vars"))
            results.append(result)
        return results
    
    # ----- Transaction -----
    
    async def transaction(self, operations: list) -> dict:
        """Execute in transaction."""
        # Note: SurrealDB supports transactions with BEGIN/COMMIT
        await self.db.query("BEGIN TRANSACTION")
        
        try:
            results = []
            for op in operations:
                result = await self.query(op["sql"], op.get("vars", {}))
                results.append(result)
            
            await self.db.query("COMMIT")
            return {"success": True, "results": results}
        except Exception as e:
            await self.db.query("CANCEL")
            return {"success": False, "error": str(e)}


async def demo():
    """Demo RPC."""
    rpc = RPCTool()
    await rpc.connect()
    
    # CRUD
    await rpc.create("user", {"name": "Alice"})
    users = await rpc.select("user")
    print(f"Users: {users}")
    
    # Graph
    await rpc.relate("user:alice", "user:bob", "follows")
    relations = await rpc.get_relations("user:alice", "follows")
    print(f"Relations: {relations}")


if __name__ == "__main__":
    asyncio.run(demo())