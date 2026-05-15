#!/usr/bin/env python3
"""
Component: ETL Pipeline

ETL pipeline component (Airbyte-style).
Based on: https://surrealdb.com/docs/build/integrations/data-management/overview
"""

import asyncio
from surrealdb import Surreal


class ETLPipeline:
    """ETL Pipeline component for SurrealDB."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "etl", "database": "pipeline"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """ETL schema."""
        schemas = [
            """
            DEFINE TABLE source SCHEMAFULL;
            DEFINE FIELD name ON source TYPE string;
            DEFINE FIELD type ON source TYPE string; -- database, api, file
            DEFINE FIELD config ON source TYPE object;
            DEFINE FIELD last_sync ON source TYPE datetime;
            """,
            """
            DEFINE TABLE destination SCHEMAFULL;
            DEFINE FIELD name ON destination TYPE string;
            DEFINE FIELD type ON destination TYPE string;
            DEFINE FIELD config ON destination TYPE object;
            """,
            """
            DEFINE TABLE pipeline SCHEMAFULL;
            DEFINE FIELD name ON pipeline TYPE string;
            DEFINE FIELD source ON pipeline TYPE record(source);
            DEFINE FIELD destination ON pipeline TYPE record(destination);
            DEFINE FIELD transform ON pipeline TYPE object;
            DEFINE FIELD schedule ON pipeline TYPE string;
            DEFINE FIELD status ON pipeline TYPE string; -- active, paused, error
            DEFINE FIELD runs ON pipeline TYPE array<object>;
            """,
            """
            DEFINE TABLE run_log SCHEMAFULL;
            DEFINE FIELD pipeline ON pipeline TYPE record(pipeline);
            DEFINE FIELD started ON run_log TYPE datetime;
            DEFINE FIELD completed ON run_log TYPE datetime;
            DEFINE FIELD records_read ON run_log TYPE int;
            DEFINE FIELD records_written ON run_log TYPE int;
            DEFINE FIELD errors ON run_log TYPE int;
            DEFINE FIELD status ON run_log TYPE string;
            """,
        ]
        
        for schema in schemas:
            await self.db.query(schema)
        print("✅ ETL schema created")
    
    # ----- Sources -----
    
    async def add_source(self, name: str, source_type: str, config: dict):
        """Add data source."""
        result = await self.db.query(
            "CREATE source SET name=$name, type=$type, config=$config",
            {"name": name, "type": source_type, "config": config}
        )
        return result[0][0]
    
    async def add_destination(self, name: str, dest_type: str, config: dict):
        """Add destination."""
        result = await self.db.query(
            "CREATE destination SET name=$name, type=$type, config=$config",
            {"name": name, "type": dest_type, "config": config}
        )
        return result[0][0]
    
    # ----- Pipeline -----
    
    async def create_pipeline(self, name: str, source_id: str, 
                        dest_id: str, transform: dict = None):
        """Create pipeline."""
        result = await self.db.query(
            """CREATE pipeline SET name=$name, source=$source, destination=$dest,
            transform=$transform, status='paused', runs=[]""",
            {"name": name, "source": source_id, "dest": dest_id, "transform": transform or {}}
        )
        return result[0][0]
    
    async def run_pipeline(self, pipeline_id: str, batch_size: int = 1000) -> dict:
        """Run one batch of pipeline."""
        # Get pipeline config
        pipeline = await self.db.query("SELECT * FROM pipeline WHERE id = $id", {"id": pipeline_id})
        if not pipeline or not pipeline[0]:
            return {"error": "Pipeline not found"}
        
        source = pipeline[0][0].get("source")
        
        # In real implementation, would fetch from source
        # For demo, simulate data
        records = [
            {"id": 1, "data": "sample1"},
            {"id": 2, "data": "sample2"},
        ]
        
        # Transform
        transform = pipeline[0][0].get("transform", {})
        if transform.get("uppercase"):
            records = [{"id": r["id"], "data": r["data"].upper()} for r in records]
        
        # Write to destination
        # In real implementation, would write to SurrealDB or other dest
        
        # Log run
        log = await self.db.query(
            """CREATE run_log SET pipeline=$pipeline, started=time::now(),
            records_read=$count, records_written=$count, errors=0, status='success'""",
            {"pipeline": pipeline_id, "count": len(records)}
        )
        
        return {
            "records_read": len(records),
            "records_written": len(records),
            "errors": 0
        }
    
    # ----- Sync -----
    
    async def sync(self, pipeline_id: str) -> dict:
        """Full sync."""
        result = await self.run_pipeline(pipeline_id)
        
        # Update source last_sync
        await self.db.query("UPDATE source SET last_sync=time::now()")
        
        return result
    
    # ----- Monitoring -----
    
    async def get_pipeline_status(self, pipeline_id: str) -> dict:
        """Get pipeline status."""
        pipeline = await self.db.query("SELECT * FROM pipeline WHERE id = $id", {"id": pipeline_id})
        
        if not pipeline or not pipeline[0]:
            return {"error": "Not found"}
        
        runs = await self.db.query(
            """SELECT * FROM run_log WHERE pipeline = $pipeline 
            ORDER BY started DESC LIMIT 10""",
            {"pipeline": pipeline_id}
        )
        
        return {
            "name": pipeline[0][0].get("name"),
            "status": pipeline[0][0].get("status"),
            "runs": runs[0] if runs else []
        }


async def demo():
    """ETL demo."""
    etl = ETLPipeline()
    await etl.connect()
    await etl.setup_schema()
    
    # Create source
    source = await etl.add_source("mysql_prod", "database", {
        "host": "localhost", "port": 3306, "database": "sales"
    })
    
    # Create dest
    dest = await etl.add_destination("surrealdb", "surrealdb", {
        "url": "ws://localhost:8000/rpc"
    })
    
    # Create pipeline
    pipeline = await etl.create_pipeline(
        "sales_sync", source["id"], dest["id"], {"uppercase": True}
    )
    
    # Run
    result = await etl.run_pipeline(pipeline["id"])
    print(f"Pipeline run: {result}")
    
    status = await etl.get_pipeline_status(pipeline["id"])
    print(f"Status: {status}")


if __name__ == "__main__":
    asyncio.run(demo())