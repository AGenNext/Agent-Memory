#!/usr/bin/env python3
"""
Sample Agent: RAG Knowledge Assistant

Based on PolyAI case study
- High-performance customer service AI
- RAG across voice AI experiences
- Low-latency responses
"""

import asyncio
from surrealdb import Surreal


class RAGAgent:
    """RAG-powered knowledge agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "rag", "database": "knowledge"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """RAG schema."""
        schemas = [
            """
            DEFINE TABLE chunk SCHEMAFULL;
            DEFINE FIELD document ON chunk TYPE string;
            DEFINE FIELD content ON chunk TYPE string;
            DEFINE FIELD embedding ON chunk TYPE array<float>;
            DEFINE FIELD source ON chunk TYPE string;
            """,
            """
            DEFINE TABLE source_document SCHEMAFULL;
            DEFINE FIELD title ON source_document TYPE string;
            DEFINE FIELD content ON source_document TYPE string;
            DEFINE FIELD url ON source_document TYPE string;
            DEFINE FIELD type ON source_document TYPE string; -- pdf, web, doc
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ RAG schema created")
    
    # ----- Ingest Documents -----
    
    async def ingest_document(self, title: str, content: str, chunk_size: int = 500) -> list:
        """Chunk and ingest document."""
        # Simple chunking
        chunks = []
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i+chunk_size]
            chunks.append({
                "document": title,
                "content": chunk,
                "embedding": [0.1] * 384,  # Would use actual embeddings
                "source": title
            })
        
        # Store chunks
        results = []
        for chunk in chunks:
            result = await self.db.query(
                "CREATE chunk SET document=$doc, content=$content, source=$source",
                {"doc": chunk["document"], "content": chunk["content"], "source": chunk["source"]}
            )
            results.append(result[0][0])
        
        return results
    
    # ----- RAG Query -----
    
    async def query(self, question: str, k: int = 5) -> dict:
        """RAG query."""
        # Get query embedding
        query_emb = [0.1] * 384  # Placeholder
        
        # Vector search
        result = await self.db.query(
            f"""SELECT *, vector::distance::knn() AS score FROM chunk 
            WHERE embedding <|{k}|> $emb ORDER BY score ASC""",
            {"emb": query_emb}
        )
        
        retrieved = result[0] if result else []
        
        # Build context
        context = "\n\n".join([c.get("content", "") for c in retrieved[:3]])
        
        return {
            "question": question,
            "context": context,
            "sources": [c.get("source") for c in retrieved[:3]],
            "answer": "Based on retrieved context..."
        }
    
    # ----- Voice AI Integration -----
    
    async def voice_query(self, audio_transcript: str) -> dict:
        """Process voice transcript."""
        return await self.query(audio_transcript)


async def demo():
    """Demo."""
    agent = RAGAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Query
    result = await agent.query("How do I reset my password?")
    print(f"Answer: {result}")


if __name__ == "__main__":
    asyncio.run(demo())