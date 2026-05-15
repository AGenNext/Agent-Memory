#!/usr/bin/env python3
"""
Plugin: Airbyte ETL

Airbyte-style ETL plugin for SurrealDB.
Based on: https://surrealdb.com/docs/build/integrations/data-management/airbyte
"""

import asyncio
from surrealdb import Surreal


class AirbytePlugin:
    """Airbyte ETL plugin."""
    
    PLUGIN_NAME = "airbyte"
    PLUGIN_VERSION = "1.0.0"
    
    def __init__(self, url: str = "ws://localhost:8000/rpc",
                 username: str = "root", password: str = "root",
                 namespace: str = "etl", database: str = "airbyte"):
        self.url = url
        self.username = username
        self.password = password
        self.namespace = namespace
        self.database = database
        self.db = None
    
    async def install(self):
        """Install plugin and create schema."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": self.namespace, "database": self.database})
        await self.db.signin({"username": self.username, "password": self.password})
        
        # Create sync tracking
        await self.db.query("""
            DEFINE TABLE _airbyte_sync SCHEMAFULL;
            DEFINE FIELD stream ON _airbyte_sync TYPE string;
            DEFINE FIELD cursor ON _airbyte_sync TYPE string;
            DEFINE FIELD last_sync ON _airbyte_sync TYPE datetime;
        """)
        
        print(f"✅ Airbyte plugin installed")
        return self
    
    # ----- Sources -----
    
    async def define_source(self, name: str, config: dict):
        """Define Airbyte source."""
        result = await self.db.query(
            "CREATE source SET name=$name, type='airbyte', config=$config",
            {"name": name, "config": config}
        )
        return result[0][0]
    
    # ----- Streams -----
    
    async def register_stream(self, stream_name: str, cursor_field: str = "updated_at"):
        """Register stream for sync."""
        result = await self.db.query(
            """CREATE _airbyte_sync SET stream=$stream, cursor=$cursor""",
            {"stream": stream_name, "cursor": cursor_field}
        )
        return result[0][0]
    
    async def sync_stream(self, stream_name: str, source_query: str) -> dict:
        """Sync stream from source to SurrealDB."""
        stream = await self.db.query(
            "SELECT * FROM _airbyte_sync WHERE stream = $stream",
            {"stream": stream_name}
        )
        
        if not stream or not stream[0]:
            return {"error": f"Stream not found: {stream_name}"}
        
        cursor = stream[0][0].get("cursor", "updated_at")
        
        # Execute source query
        await self.db.query(source_query)
        
        # Update sync time
        await self.db.query(
            """UPDATE _airbyte_sync SET last_sync=time::now() WHERE stream = $stream""",
            {"stream": stream_name}
        )
        
        return {"synced": stream_name}


async def demo():
    """Demo."""
    plugin = AirbytePlugin()
    await plugin.install()
    
    await plugin.register_stream("users", "updated_at")
    result = await plugin.sync_stream("users", "SELECT * FROM users")
    print(result)


if __name__ == "__main__":
    asyncio.run(demo())