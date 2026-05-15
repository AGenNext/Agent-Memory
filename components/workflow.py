#!/usr/bin/env python3
"""
Component: Workflow Automation (n8n-style)

Workflow automation component.
Based on: https://surrealdb.com/docs/build/integrations/data-management/n8n
"""

import asyncio
from surrealdb import Surreal


class WorkflowEngine:
    """Workflow automation engine (n8n-style)."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "workflow", "database": "automation"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Workflow schema."""
        schemas = [
            """
            DEFINE TABLE workflow SCHEMAFULL;
            DEFINE FIELD name ON workflow TYPE string;
            DEFINE FIELD definition ON workflow TYPE object;
            DEFINE FIELD active ON workflow TYPE bool DEFAULT false;
            DEFINE FIELD trigger ON workflow TYPE string;
            """,
            """
            DEFINE TABLE node SCHEMAFULL;
            DEFINE FIELD workflow ON node TYPE record(workflow);
            DEFINE FIELD id ON node TYPE string;
            DEFINE FIELD type ON node TYPE string; -- trigger, action, condition, transform
            DEFINE FIELD config ON node TYPE object;
            """,
            """
            DEFINE TABLE execution SCHEMAFULL;
            DEFINE FIELD workflow ON execution TYPE record(workflow);
            DEFINE FIELD status ON execution TYPE string; -- running, success, failed
            DEFINE FIELD input ON execution TYPE object;
            DEFINE FIELD output ON execution TYPE object;
            DEFINE FIELD started ON execution TYPE datetime;
            DEFINE FIELD completed ON execution TYPE datetime;
            """,
        ]
        
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Workflow schema created")
    
    # ----- Workflow -----
    
    async def create_workflow(self, name: str, trigger: str, nodes: list) -> dict:
        """Create workflow with nodes."""
        # Create workflow
        result = await self.db.query(
            "CREATE workflow SET name=$name, trigger=$trigger",
            {"name": name, "trigger": trigger}
        )
        workflow_id = result[0][0]["id"]
        
        # Add nodes
        for node in nodes:
            await self.db.query(
                """CREATE node SET workflow=$wf, id=$node_id, type=$type, config=$config""",
                {"wf": workflow_id, "node_id": node["id"], "type": node["type"], "config": node.get("config", {})}
            )
        
        return result[0][0]
    
    async def activate_workflow(self, workflow_id: str):
        """Activate workflow."""
        result = await self.db.query(
            "UPDATE workflow SET active = true WHERE id = $id",
            {"id": workflow_id}
        )
        return result[0][0]
    
    async def deactivate_workflow(self, workflow_id: str):
        """Deactivate workflow."""
        result = await self.db.query(
            "UPDATE workflow SET active = false WHERE id = $id",
            {"id": workflow_id}
        )
        return result[0][0]
    
    # ----- Execution -----
    
    async def execute(self, workflow_id: str, input_data: dict = None) -> dict:
        """Execute workflow."""
        # Get workflow nodes
        nodes = await self.db.query(
            "SELECT * FROM node WHERE workflow = $wf ORDER BY id",
            {"wf": workflow_id}
        )
        
        if not nodes or not nodes[0]:
            return {"error": "No nodes found"}
        
        # Execute nodes
        output = input_data or {}
        errors = []
        
        for node in nodes[0]:
            try:
                result = await self._execute_node(node, output)
                output[node["id"]] = result
            except Exception as e:
                errors.append({"node": node["id"], "error": str(e)})
        
        status = "failed" if errors else "success"
        
        # Log execution
        log = await self.db.query(
            """CREATE execution SET workflow=$wf, status=$status, input=$input,
            output=$output, started=time::now(), completed=time::now()""",
            {"wf": workflow_id, "status": status, "input": input_data, 
             "output": output}
        )
        
        return {"status": status, "output": output, "errors": errors}
    
    async def _execute_node(self, node: dict, context: dict) -> dict:
        """Execute single node."""
        node_type = node.get("type")
        config = node.get("config", {})
        
        if node_type == "trigger":
            return {"triggered": True}
        
        elif node_type == "transform":
            # Apply transformation
            if config.get("map"):
                return {"mapped": config["map"]}
            return context
        
        elif node_type == "action":
            action = config.get("action")
            if action == "query":
                # Execute query
                result = await self.db.query(config["sql"], config.get("vars", {}))
                return {"result": result[0] if result else []}
            return {"action": action}
        
        elif node_type == "condition":
            # Check condition
            if "field" in config and "value" in config:
                return {"match": context.get(config["field"]) == config["value"]}
            return {"condition": True}
        
        return {"executed": node_type}
    
    # ----- Webhooks -----
    
    async def trigger_webhook(self, workflow_id: str, payload: dict) -> dict:
        """Trigger workflow via webhook (for active workflows)."""
        workflow = await self.db.query(
            "SELECT * FROM workflow WHERE id = $id AND active = true",
            {"id": workflow_id}
        )
        
        if not workflow or not workflow[0]:
            return {"error": "Workflow not active"}
        
        # Execute
        return await self.execute(workflow_id, payload)
    
    # ----- Monitoring -----
    
    async def get_executions(self, workflow_id: str, limit: int = 10) -> list:
        """Get recent executions."""
        result = await self.db.query(
            """SELECT * FROM execution WHERE workflow = $wf 
            ORDER BY started DESC LIMIT $limit""",
            {"wf": workflow_id, "limit": limit}
        )
        return result[0] if result else []


async def demo():
    """Workflow demo."""
    engine = WorkflowEngine()
    await engine.connect()
    await engine.setup_schema()
    
    # Create workflow with nodes
    workflow = await engine.create_workflow(
        "data_processor",
        "webhook",
        [
            {"id": "1", "type": "trigger", "config": {}},
            {"id": "2", "type": "transform", "config": {"map": "processed"}},
            {"id": "3", "type": "action", "config": {
                "action": "query", "sql": "SELECT * FROM user LIMIT 10"
            }},
        ]
    )
    
    print(f"Workflow: {workflow['name']}")
    
    # Execute
    result = await engine.execute(workflow["id"], {"test": "data"})
    print(f"Execution: {result['status']}")


if __name__ == "__main__":
    asyncio.run(demo())