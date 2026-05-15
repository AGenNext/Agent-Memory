#!/usr/bin/env python3
"""
Tool: Streaming

WebSocket streaming capability.
Reference: https://surrealdb.com/use-cases/real-time
"""

import asyncio
from surrealdb import Surreal
from typing import AsyncIterator, Callable


class StreamingTool:
    """Streaming tool for SurrealDB."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
        self.streams = {}
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "streaming", "database": "live"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- Stream Table -----
    
    async def stream_table(self, table: str) -> AsyncIterator[dict]:
        """Stream entire table in real-time."""
        query = f"LIVE SELECT * FROM {table}"
        
        async for change in self.db.live(query):
            yield {
                "action": "change",
                "table": table,
                "data": change
            }
    
    async def stream_changelog(self, table: str) -> AsyncIterator[dict]:
        """Stream with change log."""
        query = f"LIVE SELECT * FROM {table}"
        
        async for change in self.db.live(query):
            yield {
                "id": change.get("id"),
                "action": change.get("action"),  # CREATE, UPDATE, DELETE
                "old": change.get("old"),
                "new": change.get("new"),
                "timestamp": change.get("timestamp")
            }
    
    # ----- Filtered Streams -----
    
    async def stream_where(self, table: str, where: str) -> AsyncIterator[dict]:
        """Stream filtered results."""
        query = f"LIVE SELECT * FROM {table} WHERE {where}"
        
        async for change in self.db.live(query):
            yield change
    
    async def stream_field(self, table: str, field: str) -> AsyncIterator:
        """Stream specific field changes."""
        query = f"LIVE SELECT {field} FROM {table}"
        
        async for change in self.db.live(query):
            yield {field: change.get(field)}
    
    # ----- Multi-Table Stream -----
    
    async def stream_multiple(self, tables: list) -> AsyncIterator[dict]:
        """Stream from multiple tables."""
        for table in tables:
            query = f"LIVE SELECT * FROM {table}"
            
            async for change in self.db.live(query):
                yield {
                    "source": table,
                    "data": change
                }
    
    # ----- Common Patterns -----
    
    async def stream_chat(self, room: str) -> AsyncIterator[dict]:
        """Stream chat messages."""
        query = f"LIVE SELECT * FROM message WHERE room = 'room:{room}' ORDER BY created DESC"
        
        async for msg in self.db.live(query):
            yield msg
    
    async def stream_orders(self, status: str = None) -> AsyncIterator[dict]:
        """Stream order updates."""
        if status:
            query = f"LIVE SELECT * FROM order WHERE status = '{status}'"
        else:
            query = "LIVE SELECT * FROM order"
        
        async for order in self.db.live(query):
            yield order
    
    async def stream_telemetry(self, device_id: str) -> AsyncIterator[dict]:
        """Stream IoT telemetry."""
        query = f"LIVE SELECT * FROM telemetry WHERE device = 'device:{device_id}' ORDER BY timestamp DESC"
        
        async for data in self.db.live(query):
            yield {
                "device": device_id,
                "metrics": data,
                "timestamp": data.get("timestamp")
            }
    
    # ----- Batch Stream -----
    
    async def stream_batch(self, table: str, batch_size: int = 100) -> AsyncIterator[list]:
        """Stream in batches."""
        query = f"LIVE SELECT * FROM {table} LIMIT {batch_size}"
        
        batch = []
        async for change in self.db.live(query):
            batch.append(change)
            
            if len(batch) >= batch_size:
                yield batch
                batch = []
        
        if batch:
            yield batch
    
    # ----- Aggregation Stream -----
    
    async def stream_aggregated(self, table: str, group_by: str, 
                          field: str, op: str = "count") -> AsyncIterator[dict]:
        """Stream aggregated counts."""
        # Uses live queries with aggregation
        query = f"LIVE SELECT {group_by}, {op}({field}) AS aggregate FROM {table} GROUP BY {group_by}"
        
        async for result in self.db.live(query):
            yield result
    
    # ----- Transform Stream -----
    
    async def stream_transform(self, table: str, 
                          transform: Callable) -> AsyncIterator:
        """Stream with transformation."""
        query = f"LIVE SELECT * FROM {table}"
        
        async for change in self.db.live(query):
            yield await transform(change)


async def transform_order(order: dict) -> dict:
    """Example transform."""
    return {
        "id": order.get("id"),
        "total": order.get("total", 0),
        "status": order.get("status"),
        "display": f"#{order.get('id')}: {order.get('total')}"
    }


async def demo():
    """Demo streaming."""
    stream = StreamingTool()
    await stream.connect()
    
    print("Streaming ready")
    print("""
Usage:
    async for msg in stream.stream_chat("general"):
        print(msg)
    
    async for data in stream.stream_telemetry("sensor_1"):
        print(data)
    """)


if __name__ == "__main__":
    asyncio.run(demo())