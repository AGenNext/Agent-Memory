#!/usr/bin/env python3
"""
Sample Agent: Knowledge Graph Insights

Based on Samsung case study
- Real-time audience insights
- Ad targeting with knowledge graph
"""

import asyncio
from surrealdb import Surreal


class KnowledgeGraphAgent:
    """Knowledge graph insights agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "knowledge", "database": "insights"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Knowledge graph schema."""
        schemas = [
            """
            DEFINE TABLE user SCHEMAFULL;
            DEFINE FIELD name ON user TYPE string;
            DEFINE FIELD demographics ON user TYPE object;
            DEFINE FIELD interests ON user TYPE array<string>;
            """,
            """
            DEFINE TABLE audience SCHEMAFULL;
            DEFINE FIELD name ON audience TYPE string;
            DEFINE FIELD criteria ON audience TYPE object;
            """,
            """
            DEFINE TABLE content SCHEMAFULL;
            DEFINE FIELD title ON content TYPE string;
            DEFINE FIELD category ON content TYPE string;
            DEFINE FIELD embedding ON content TYPE array<float>;
            """,
            """
            DEFINE TABLE interested_in TYPE RELATION FROM user TO audience;
            DEFINE FIELD strength ON interested_in TYPE float;
            """,
            """
            DEFINE TABLE watches TYPE RELATION FROM user TO content;
            DEFINE FIELD duration ON watches TYPE int;
            DEFINE FIELD timestamp ON watches TYPE datetime;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Knowledge graph schema created")
    
    # ----- Audience -----
    
    async def create_audience(self, name: str, criteria: dict) -> dict:
        """Create audience segment."""
        result = await self.db.query(
            "CREATE audience SET name=$name, criteria=$criteria",
            {"name": name, "criteria": criteria}
        )
        return result[0][0]
    
    async def find_audience(self, user_id: str, min_strength: float = 0.5) -> list:
        """Find audiences for user."""
        result = await self.db.query(
            """SELECT ->interested_in[WHERE strength > $min]->audience.name AS audiences
            FROM user:$id""",
            {"id": user_id, "min": min_strength}
        )
        return result[0] if result else []
    
    # ----- Insights -----
    
    async def get_insights(self) -> dict:
        """Get audience insights."""
        # Total users
        users = await self.db.query("SELECT count() AS total FROM user")
        
        # Top interests
        interests = await self.db.query(
            """SELECT interest, count() AS count FROM user, 
            interests GROUP BY interest ORDER BY count DESC LIMIT 10"""
        )
        
        return {
            "total_users": users[0][0].get("total", 0) if users else 0,
            "top_interests": interests[0] if interests else [],
        }
    
    # ----- Content Recommendations -----
    
    async def recommend_content(self, user_id: str, k: int = 5) -> list:
        """Recommend content based on graph."""
        # Get user interests
        user = await self.db.query(
            "SELECT interests FROM user WHERE id = $id",
            {"id": user_id}
        )
        
        if not user or not user[0]:
            return []
        
        interests = user[0][0].get("interests", [])
        
        # Find related content
        results = []
        for interest in interests[:3]:
            result = await self.db.query(
                "SELECT * FROM content WHERE category = $cat LIMIT $k",
                {"cat": interest, "k": k}
            )
            if result and result[0]:
                results.extend(result[0])
        
        return results[:k]


async def demo():
    """Demo."""
    agent = KnowledgeGraphAgent()
    await agent.connect()
    await agent.setup_schema()
    
    insights = await agent.get_insights()
    print(f"Insights: {insights}")


if __name__ == "__main__":
    asyncio.run(demo())