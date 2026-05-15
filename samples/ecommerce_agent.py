#!/usr/bin/env python3
"""
Sample Agent: E-Commerce Recommendation

Based on Saks Fifth Avenue case study
- Personalized shopping experiences
- AI-driven real-time recommendations
- Luxury e-commerce
"""

import asyncio
from surrealdb import Surreal


class EcommerceAgent:
    """E-commerce recommendation agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "ecommerce", "database": "recommendations"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """E-commerce schema."""
        schemas = [
            """
            DEFINE TABLE product SCHEMAFULL;
            DEFINE FIELD name ON product TYPE string;
            DEFINE FIELD category ON product TYPE string;
            DEFINE FIELD price ON product TYPE float;
            DEFINE FIELD brand ON product TYPE string;
            DEFINE FIELD embedding ON product TYPE array<float>;
            """,
            """
            DEFINE TABLE customer SCHEMAFULL;
            DEFINE FIELD name ON customer TYPE string;
            DEFINE FIELD email ON customer TYPE string;
            DEFINE FIELD preferences ON customer TYPE array<string>;
            DEFINE FIELD history ON customer TYPE array<string>;
            """,
            """
            DEFINE TABLE interaction SCHEMAFULL;
            DEFINE FIELD customer ON interaction TYPE record(customer);
            DEFINE FIELD product ON interaction TYPE record(product);
            DEFINE FIELD type ON interaction TYPE string; -- view, cart, purchase
            DEFINE FIELD timestamp ON interaction TYPE datetime;
            """,
            """
            DEFINE TABLE recommendation SCHEMAFULL;
            DEFINE FIELD customer ON recommendation TYPE record(customer);
            DEFINE FIELD products ON recommendation TYPE array<string>;
            DEFINE FIELD reason ON recommendation TYPE string;
            DEFINE FIELD generated ON recommendation TYPE datetime;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ E-commerce schema created")
    
    # ----- Recommendations -----
    
    async def get_recommendations(self, customer_id: str, k: int = 5) -> list:
        """Get personalized recommendations."""
        # Get customer history
        history = await self.db.query(
            "SELECT history FROM customer WHERE id = $id",
            {"id": customer_id}
        )
        
        # Vector search for similar products
        query_emb = [0.1] * 384  # Placeholder
        result = await self.db.query(
            f"""SELECT *, vector::distance::knn() AS score FROM product 
            WHERE embedding <|{k}|> $emb ORDER BY score ASC""",
            {"emb": query_emb}
        )
        
        return result[0] if result else []
    
    # ----- Track Interaction -----
    
    async def track_interaction(self, customer_id: str, product_id: str, type: str):
        """Track customer interaction."""
        result = await self.db.query(
            """CREATE interaction SET customer=$customer, product=$product, 
            type=$type, timestamp=time::now()""",
            {"customer": customer_id, "product": product_id, "type": type}
        )
        return result[0][0]
    
    # ----- Real-Time Personalization -----
    
    async def personalize_homepage(self, customer_id: str) -> dict:
        """Generate personalized homepage."""
        recs = await self.get_recommendations(customer_id, k=10)
        
        return {
            "customer": customer_id,
            "recommended": recs[:5],
            "trending": await self.get_trending(),
            "categories": await self.get_categories()
        }
    
    async def get_trending(self) -> list:
        """Get trending products."""
        result = await self.db.query(
            """SELECT product, count() AS views FROM interaction 
            WHERE type = 'view' GROUP BY product ORDER BY views DESC LIMIT 10"""
        )
        return result[0] if result else []
    
    async def get_categories(self) -> list:
        """Get all categories."""
        result = await self.db.query(
            "SELECT category, count() AS count FROM product GROUP BY category"
        )
        return result[0] if result else []


async def demo():
    """Demo."""
    agent = EcommerceAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Get homepage
    page = await agent.personalize_homepage("customer:alice")
    print(f"Homepage: {page}")


if __name__ == "__main__":
    asyncio.run(demo())