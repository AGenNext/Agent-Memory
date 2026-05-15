#!/usr/bin/env python3
"""
Sample Agent: Digital Twin Agent

Based on: "Digital twins"
- IoT device simulation
- State tracking
- Time-series
"""

import asyncio
from surrealdb import Surreal


class DigitalTwinAgent:
    """Digital twin agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "digital_twin", "database": "devices"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Digital twin schema."""
        schemas = [
            """
            DEFINE TABLE device SCHEMAFULL;
            DEFINE FIELD name ON device TYPE string;
            DEFINE FIELD type ON device TYPE string;
            DEFINE FIELD location ON device TYPE object;
            DEFINE FIELD state ON device TYPE object;
            """,
            """
            DEFINE TABLE telemetry SCHEMAFULL;
            DEFINE FIELD device ON telemetry TYPE record(device);
            DEFINE FIELD metric ON telemetry TYPE string;
            DEFINE FIELD value ON telemetry TYPE float;
            DEFINE FIELD unit ON telemetry TYPE string;
            DEFINE FIELD timestamp ON telemetry TYPE datetime;
            """,
            """
            DEFINE TABLE alert SCHEMAFULL;
            DEFINE FIELD device ON alert TYPE record(device);
            DEFINE FIELD severity ON alert TYPE string;
            DEFINE FIELD message ON alert TYPE string;
            DEFINE FIELD acknowledged ON alert TYPE bool DEFAULT false;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Digital twin schema created")
    
    # ----- Device -----
    
    async def register_device(self, name: str, device_type: str,
                       location: dict = None) -> dict:
        """Register device."""
        result = await self.db.query(
            """CREATE device SET name=$name, type=$type, location=$loc, state={}""",
            {"name": name, "type": device_type, "loc": location or {}}
        )
        return result[0][0]
    
    async def update_state(self, device_id: str, state: dict) -> dict:
        """Update device state."""
        result = await self.db.query(
            "UPDATE device SET state=$state WHERE id = $id",
            {"id": device_id, "state": state}
        )
        return result[0][0]
    
    # ----- Telemetry -----
    
    async def record_telemetry(self, device_id: str, metric: str,
                             value: float, unit: str) -> dict:
        """Record telemetry."""
        result = await self.db.query(
            """CREATE telemetry SET device=$device, metric=$metric, value=$value,
            unit=$unit, timestamp=time::now()""",
            {"device": device_id, "metric": metric, "value": value, "unit": unit}
        )
        return result[0][0]
    
    async def get_telemetry(self, device_id: str, metric: str = None,
                          limit: int = 100) -> list:
        """Get device telemetry."""
        if metric:
            result = await self.db.query(
                f"""SELECT * FROM telemetry WHERE device = $device AND metric = $metric
                ORDER BY timestamp DESC LIMIT {limit}""",
                {"device": device_id, "limit": limit}
            )
        else:
            result = await self.db.query(
                f"""SELECT * FROM telemetry WHERE device = $device
                ORDER BY timestamp DESC LIMIT {limit}""",
                {"device": device_id, "limit": limit}
            )
        return result[0] if result else []
    
    # ----- Alerts -----
    
    async def check_alerts(self, device_id: str) -> list:
        """Check for alert conditions."""
        # Get latest telemetry
        temp = await self.get_telemetry(device_id, "temperature", 1)
        
        if temp:
            value = temp[0].get("value", 0)
            if value > 90:
                alert = await self.db.query(
                    """CREATE alert SET device=$device, severity='critical',
                    message='High temperature'""",
                    {"device": device_id}
                )
                return alert[0]
        
        return []
    
    # ----- Query -----
    
    async def get_all_devices(self) -> list:
        """Get all devices."""
        result = await self.db.query("SELECT * FROM device")
        return result[0] if result else []


async def demo():
    """Demo."""
    agent = DigitalTwinAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Register device
    device = await agent.register_device("sensor_1", "temperature", {"room": "lab"})
    print(f"Device: {device['id']}")


if __name__ == "__main__":
    asyncio.run(demo())