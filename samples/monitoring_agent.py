#!/usr/bin/env python3
"""
Sample Agent: Real-Time Monitoring

Based on Tencent case study
- Unified infrastructure monitoring
- Real-time platform
- 9 tools → 1
"""

import asyncio
from surrealdb import Surreal


class MonitoringAgent:
    """Real-time monitoring agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "monitoring", "database": "infrastructure"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Monitoring schema."""
        schemas = [
            """
            DEFINE TABLE metric SCHEMAFULL;
            DEFINE FIELD service ON metric TYPE string;
            DEFINE FIELD host ON metric TYPE string;
            DEFINE FIELD cpu ON metric TYPE float;
            DEFINE FIELD memory ON metric TYPE float;
            DEFINE FIELD latency ON metric TYPE float;
            DEFINE FIELD timestamp ON metric TYPE datetime;
            """,
            """
            DEFINE TABLE alert SCHEMAFULL;
            DEFINE FIELD service ON alert TYPE string;
            DEFINE FIELD severity ON alert TYPE string; -- critical, warning, info
            DEFINE FIELD message ON alert TYPE string;
            DEFINE FIELD timestamp ON alert TYPE datetime;
            DEFINE FIELD acknowledged ON alert TYPE bool DEFAULT false;
            """,
            """
            DEFINE TABLE service SCHEMAFULL;
            DEFINE FIELD name ON service TYPE string;
            DEFINE FIELD status ON service TYPE string; -- healthy, degraded, down
            DEFINE FIELD region ON service TYPE string;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Monitoring schema created")
    
    # ----- Metrics -----
    
    async def record_metric(self, service: str, host: str, cpu: float, 
                   memory: float, latency: float) -> dict:
        """Record metric."""
        result = await self.db.query(
            """CREATE metric SET service=$service, host=$host, cpu=$cpu, 
            memory=$memory, latency=$latency, timestamp=time::now()""",
            {"service": service, "host": host, "cpu": cpu, 
             "memory": memory, "latency": latency}
        )
        return result[0][0]
    
    # ----- Alerts -----
    
    async def create_alert(self, service: str, severity: str, message: str) -> dict:
        """Create alert."""
        result = await self.db.query(
            """CREATE alert SET service=$service, severity=$severity, 
            message=$message, timestamp=time::now()""",
            {"service": service, "severity": severity, "message": message}
        )
        return result[0][0]
    
    async def get_active_alerts(self) -> list:
        """Get active alerts."""
        result = await self.db.query(
            "SELECT * FROM alert WHERE acknowledged = false ORDER BY timestamp DESC"
        )
        return result[0] if result else []
    
    # ----- Health Check -----
    
    async def check_service(self, service: str) -> dict:
        """Check service health."""
        # Get latest metric
        metric = await self.db.query(
            "SELECT * FROM metric WHERE service = $service ORDER BY timestamp DESC LIMIT 1",
            {"service": service}
        )
        
        if not metric or not metric[0]:
            return {"service": service, "status": "unknown"}
        
        m = metric[0][0]
        cpu = m.get("cpu", 0)
        
        # Determine status
        if cpu > 90:
            status = "critical"
            await self.create_alert(service, "critical", f"High CPU: {cpu}%")
        elif cpu > 75:
            status = "warning"
        else:
            status = "healthy"
        
        return {
            "service": service,
            "status": status,
            "cpu": cpu,
            "memory": m.get("memory"),
            "latency": m.get("latency")
        }
    
    # ----- Unified Dashboard -----
    
    async def dashboard(self) -> dict:
        """Get unified dashboard."""
        # Get services
        services = await self.db.query("SELECT * FROM service")
        
        # Get alerts
        alerts = await self.get_active_alerts()
        
        # Health summary
        healthy = 0
        degraded = 0
        down = 0
        
        return {
            "services": services[0] if services else [],
            "active_alerts": alerts,
            "healthy": healthy,
            "degraded": degraded,
            "down": down
        }


async def demo():
    """Demo."""
    agent = MonitoringAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Dashboard
    dash = await agent.dashboard()
    print(f"Dashboard: {dash}")


if __name__ == "__main__":
    asyncio.run(demo())