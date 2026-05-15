#!/usr/bin/env python3
"""
Sample Agent: Analytics Dashboard

Based on blog: "Exponential cost traps"
- Unified analytics
- No ETL pipelines
- Multi-model analytics
"""

import asyncio
from surrealdb import Surreal


class AnalyticsAgent:
    """Unified analytics agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "analytics", "database": "unified"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Unified analytics schema."""
        schemas = [
            """
            DEFINE TABLE event SCHEMAFULL;
            DEFINE FIELD type ON event TYPE string; -- click, view, purchase
            DEFINE FIELD user_id ON event TYPE string;
            DEFINE FIELD properties ON event TYPE object;
            DEFINE FIELD timestamp ON event TYPE datetime;
            """,
            """
            DEFINE TABLE user_activity SCHEMAFULL;
            DEFINE FIELD user_id ON user_activity TYPE string;
            DEFINE FIELD daily_active ON user_activity TYPE int;
            DEFINE FIELD session_time ON user_activity TYPE int;
            DEFINE FIELD events ON user_activity TYPE array<string>;
            """,
            """
            DEFINE TABLE metric SCHEMAFULL;
            DEFINE FIELD name ON metric TYPE string;
            DEFINE FIELD value ON metric TYPE float;
            DEFINE FIELD dimensions ON metric TYPE object;
            DEFINE FIELD timestamp ON metric TYPE datetime;
            """,
            """
            DEFINE TABLE aggregation SCHEMAFULL;
            DEFINE FIELD name ON aggregation TYPE string;
            DEFINE FIELD query ON aggregation TYPE string;
            DEFINE FIELD result ON aggregation TYPE object;
            DEFINE FIELD updated ON aggregation TYPE datetime;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Unified analytics schema created")
    
    # ----- Event Tracking -----
    
    async def track_event(self, event_type: str, user_id: str, 
                    properties: dict = None) -> dict:
        """Track event."""
        result = await self.db.query(
            """CREATE event SET type=$type, user_id=$user, 
            properties=$props, timestamp=time::now()""",
            {"type": event_type, "user": user_id, "props": properties or {}}
        )
        return result[0][0]
    
    # ----- Real-Time Aggregations -----
    
    async def count_dau(self) -> int:
        """Daily active users."""
        result = await self.db.query(
            """SELECT count() AS dau FROM event 
            WHERE timestamp > time::now() - 24h"""
        )
        return result[0][0].get("dau", 0) if result else 0
    
    async def count_events(self, event_type: str = None) -> int:
        """Count events by type."""
        if event_type:
            result = await self.db.query(
                "SELECT count() AS count FROM event WHERE type = $type",
                {"type": event_type}
            )
        else:
            result = await self.db.query(
                "SELECT count() AS count FROM event"
            )
        return result[0][0].get("count", 0) if result else 0
    
    async def revenue_today(self) -> float:
        """Calculate today's revenue."""
        result = await self.db.query(
            """SELECT math::sum(properties.total) AS revenue FROM event 
            WHERE type = 'purchase' AND timestamp > time::now() - 24h"""
        )
        return result[0][0].get("revenue", 0) if result else 0
    
    async def top_users(self, k: int = 10) -> list:
        """Top users by activity."""
        result = await self.db.query(
            f"""SELECT user_id, count() AS events FROM event 
            GROUP BY user_id ORDER BY events DESC LIMIT {k}"""
        )
        return result[0] if result else []
    
    # ----- Dashboard -----
    
    async def dashboard(self) -> dict:
        """Get full dashboard."""
        return {
            "dau": await self.count_dau(),
            "total_events": await self.count_events(),
            "revenue": await self.revenue_today(),
            "top_users": await self.top_users(),
            "timestamp": "now"
        }


async def demo():
    """Demo."""
    agent = AnalyticsAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Track event
    await agent.track_event("purchase", "user_123", {"total": 99.99})
    
    # Get dashboard
    dash = await agent.dashboard()
    print(f"Dashboard: {dash}")


if __name__ == "__main__":
    asyncio.run(demo())