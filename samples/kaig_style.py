#!/usr/bin/env python3
"""
Kai G Style Agent - Sample Agent with SurrealDB

This is a simplified version inspired by surrealdb/kaig
"""

import asyncio
from typing import Any, Optional


class DB:
    """Simple database wrapper"""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc", 
                 user: str = "root", password: str = "root",
                 namespace: str = "memory", database: str = "agent"):
        self.url = url
        self.user = user
        self.password = password
        self.ns = namespace
        self.db = database
        self._conn = None
    
    async def connect(self):
        from surrealdb import Surreal
        self._conn = Surreal(self.url)
        await self._conn.connect()
        await self._conn.use({"namespace": self.ns, "database": self.db})
        await self._conn.signin({"username": self.user, "password": self.password})
        return self
    
    async def query(self, query: str, vars: dict = None):
        if not self._conn:
            await self.connect()
        return await self._conn.query(query, vars)
    
    async def apply_schema(self, tables: list[str] = None):
        """Apply schema"""
        schemas = tables or [
            """
            DEFINE TABLE document SCHEMAFULL;
            DEFINE FIELD title ON document TYPE string;
            DEFINE FIELD content ON document TYPE string;
            DEFINE FIELD embedding ON document TYPE array<float>;
            DEFINE FIELD keywords ON document TYPE array<string>;
            """,
            """
            DEFINE TABLE keyword SCHEMAFULL;
            DEFINE FIELD name ON keyword TYPE string;
            """,
            """
            DEFINE TABLE has_keyword TYPE RELATION FROM document TO keyword;
            """,
            """
            DEFINE INDEX doc_vec ON document FIELDS embedding HNSW DIMENSION 384 DISTANCE COSINE;
            """,
        ]
        for schema in schemas:
            await self.query(schema)
        print("✅ Schema applied")


class KaiGAgent:
    """
    Kai G style agent with tools.
    
    Inspired by surrealdb/kaig
    """
    
    def __init__(self, db: DB, llm_provider: str = "openai"):
        self.db = db
        self.llm_provider = llm_provider
        self.tools = [
            self.search_documents,
            self.create_document,
            self.manage_keywords,
        ]
    
    async def search_documents(self, query: str, k: int = 5) -> list:
        """
        Search documents by similarity.
        
        Usage: "Find documents about X"
        """
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI()
            
            # Get embedding
            emb = (await client.embeddings.create(
                model="text-embedding-3-small",
                input=query
            )).data[0].embedding
            
            # Search
            results = await self.db.query(
                """SELECT *, vector::distance::knn() AS score 
                FROM document WHERE embedding <|$k|> $emb
                ORDER BY score ASC LIMIT $k""",
                {"k": k, "emb": emb}
            )
            
            return results[0] if results else []
        except Exception as e:
            return [{"error": str(e)}]
    
    async def create_document(self, title: str, content: str, keywords: list = None) -> dict:
        """
        Create document with embeddings.
        
        Usage: "Store document about X"
        """
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI()
            
            # Embed
            emb = (await client.embeddings.create(
                model="text-embedding-3-small",
                input=content
            )).data[0].embedding
            
            # Store
            result = await self.db.query(
                """CREATE document SET title = $title, content = $content, 
                embedding = $emb, keywords = $keywords""",
                {"title": title, "content": content, "emb": emb, "keywords": keywords or []}
            )
            
            return {"success": True, "id": result[0][0].get("id")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def manage_keywords(self, action: str, document: str, keywords: list) -> dict:
        """
        Link keywords to documents.
        
        Usage: "Tag document with keywords"
        """
        results = []
        for kw in keywords:
            if action == "add":
                # Create keyword
                await self.db.query(
                    "CREATE keyword:$kw SET name = $name",
                    {"name": kw}
                )
                # Link
                await self.db.query(
                    f"RELATE document:$document -> has_keyword -> keyword:$kw",
                )
                results.append(f"Linked {document} to {kw}")
        
        return {"success": True, "results": results}
    
    async def run(self, task: str) -> dict:
        """
        Run agent task.
        
        Args:
            task: Natural language task
        """
        task_lower = task.lower()
        
        if "search" in task_lower or "find" in task_lower:
            # Extract query
            query = task.replace("search", "").replace("find", "").strip()
            return await self.search_documents(query)
        
        elif "create" in task_lower or "store" in task_lower:
            # Extract title and content
            return await self.create_document(
                title="Document",  # Would parse from task
                content=task
            )
        
        elif "tag" in task_lower or "keyword" in task_lower:
            return await self.manage_keywords("add", "doc1", ["tag"])
        
        return {"message": "Task not recognized"}


# Example usage
async def main():
    """Example run"""
    print("="*50)
    print("Kai G Agent Example")
    print("="*50)
    
    # Initialize
    db = DB()
    await db.connect()
    
    # Apply schema
    await db.apply_schema()
    
    # Create agent
    agent = KaiGAgent(db)
    
    # Add sample document
    doc = await agent.create_document(
        title="AI Agents",
        content="AI agents are software programs that can autonomously interact with databases and external systems.",
        keywords=["AI", "agents", "machine-learning"]
    )
    print(f"\nCreated: {doc}")
    
    # Search
    results = await agent.search_documents("artificial intelligence agents", k=3)
    print(f"\nSearch results: {results[:3] if results else 'None'}")
    
    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())