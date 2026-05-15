#!/usr/bin/env python3
"""
Plugin: n8n Workflow Automation

n8n-style workflow automation for SurrealDB.
Based on: https://surrealdb.com/docs/build/integrations/data-management/n8n
"""

import asyncio
from surrealdb import Surreal


class N8nPlugin:
    """n8n workflow automation plugin."""
    
    PLUGIN_NAME = "n8n"
    PLUGIN_VERSION = "1.0.0"
    
    # Built-in node types
    NODE_TYPES = [
        "trigger",        # Webhook, schedule, manual
        "if",            # Conditional branch
        "merge",         # Combine branches
        "http_request",  # Call external API
        "database",      # Query SurrealDB
        "transform",    # Transform data
        "set",          # Set variable
        "log",          # Log output
    ]
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def install(self):
        """Install plugin."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "workflows", "database": "n8n"})
        await self.db.signin({"username": "root", "password": "root"})
        
        # Workflow storage
        await self.db.query("""
            DEFINE TABLE _n8n_workflow SCHEMAFULL;
            DEFINE FIELD name ON _n8n_workflow TYPE string;
            DEFINE FIELD nodes ON _n8n_workflow TYPE array<object>;
            DEFINE FIELD connections ON _n8n_workflow TYPE array<object>;
            DEFINE FIELD active ON _n8n_workflow TYPE bool DEFAULT false;
        """)
        
        print(f"✅ n8n plugin installed")
        return self
    
    # ----- Workflow Management -----
    
    async def create_workflow(self, name: str, nodes: list, connections: list) -> dict:
        """Create n8n workflow."""
        result = await self.db.query(
            """CREATE _n8n_workflow SET name=$name, nodes=$nodes, 
            connections=$connections""",
            {"name": name, "nodes": nodes, "connections": connections}
        )
        return result[0][0]
    
    async def activate(self, workflow_id: str):
        """Activate workflow."""
        await self.db.query(
            "UPDATE _n8n_workflow SET active = true WHERE id = $id",
            {"id": workflow_id}
        )
    
    async def deactivate(self, workflow_id: str):
        """Deactivate workflow."""
        await self.db.query(
            "UPDATE _n8n_workflow SET active = false WHERE id = $id",
            {"id": workflow_id}
        )
    
    # ----- Execute -----
    
    async def execute(self, workflow_id: str, input_data: dict = None) -> dict:
        """Execute workflow."""
        workflow = await self.db.query(
            "SELECT * FROM _n8n_workflow WHERE id = $id",
            {"id": workflow_id}
        )
        
        if not workflow or not workflow[0]:
            return {"error": "Not found"}
        
        wf = workflow[0][0]
        nodes = wf.get("nodes", [])
        connections = wf.get("connections", [])
        
        # Build execution graph
        output = input_data or {}
        
        for node in nodes:
            if node["type"] == "trigger":
                output[node["id"]] = {"triggered": True}
            elif node["type"] == "database":
                result = await self.db.query(
                    node.get("query", "SELECT * FROM none LIMIT 1")
                )
                output[node["id"]] = {"result": result[0] if result else []}
            elif node["type"] == "set":
                output[node["id"]] = {node["name"]: node.get("value")}
            elif node["type"] == "transform":
                # Simple transform
                output[node["id"]] = output.get("input", {})
        
        return {"output": output}
    
    # ----- Webhook Trigger -----
    
    async def trigger(self, workflow_id: str, payload: dict) -> dict:
        """Trigger via webhook."""
        workflow = await self.db.query(
            "SELECT * FROM _n8n_workflow WHERE id = $id AND active = true",
            {"id": workflow_id}
        )
        
        if not workflow or not workflow[0]:
            return {"error": "Workflow not active"}
        
        return await self.execute(workflow_id, payload)


async def demo():
    """Demo."""
    plugin = N8nPlugin()
    await plugin.install()
    
    # Create workflow
    workflow = await plugin.create_workflow(
        "user_processor",
        nodes=[
            {"id": "1", "type": "trigger", "name": "Webhook"},
            {"id": "2", "type": "set", "name": "user", "value": "{{$json.name}}"},
            {"id": "3", "type": "database", "query": "SELECT * FROM user"},
        ],
        connections=[{"from": "1", "to": "2"}, {"from": "2", "to": "3"}]
    )
    
    # Execute
    result = await plugin.execute(workflow["id"], {"name": "Alice"})
    print(result)


if __name__ == "__main__":
    asyncio.run(demo())