#!/usr/bin/env python3
"""
Sample Agent: Hybrid Search

Based on blog: "Hybrid search inside SurrealDB"
- HNSW + BM25 combined
- Reranking
- Vector + full-text
"""

import asyncio
from surrealdb import Surreal


class HybridSearchAgent:
    """Hybrid search agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "hybrid", "database": "search"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Hybrid search schema."""
        schemas = [
            """
            DEFINE TABLE doc SCHEMAFULL;
            DEFINE FIELD title ON doc TYPE string;
            DEFINE FIELD content ON doc TYPE string;
            DEFINE FIELD tags ON doc TYPE array<string>;
            DEFINE FIELD embedding ON doc TYPE array<float>;
            """,
        ]
        
        # Create indexes
        await self.db.query("""
            DEFINE ANALYZER my_analyzer TOKENIZER basic FILTERS lowercase, ascii;
        """)
        
        await self.db.query("""
            DEFINE INDEX doc_text ON doc FIELDS content SEARCH ANALYZER my_analyzer BM15;
        """)
        
        await self.db.query("""
            DEFINE INDEX doc_vec ON doc FIELDS embedding HNSW DIMENSION 384 DISTANCE COSINE;
        """)
        
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Hybrid search schema created")
    
    # ----- Index Documents -----
    
    async def index_document(self, title: str, content: str, 
                        tags: list = None) -> dict:
        """Index document."""
        result = await self.db.query(
            """CREATE doc SET title=$title, content=$content, tags=$tags""",
            {"title": title, "content": content, "tags": tags or []}
        )
        return result[0][0]
    
    # ----- Hybrid Search -----
    
    async def hybrid_search(self, query: str, k: int = 10) -> list:
        """Hybrid search with reranking."""
        query_emb = [0.1] * 384  # Would use actual embedding
        
        # BM25 search
        bm25_result = await self.db.query(f"""
            SELECT *, search::score() AS bm25
            FROM doc WHERE content @@ $query
            ORDER BY bm25 DESC LIMIT {k}
        """, {"query": query})
        
        # Vector search
        vec_result = await self.db.query(f"""
            SELECT *, vector::distance::knn() AS cosim
            FROM doc WHERE embedding <|{k}|> $emb
            ORDER BY cosim ASC
        """, {"emb": query_emb})
        
        # RRF fusion
        if bm25_result and vec_result:
            combined = await self.db.query("""
                SELECT * FROM search::rrf([$bm25, $vec], 5, 20)
            """, {"bm25": bm25_result[0], "vec": vec_result[0]})
            return combined[0] if combined else []
        
        return bm25_result[0] if bm25_result else []
    
    # ----- Vector Only -----
    
    async def vector_search(self, query: str, k: int = 5) -> list:
        """Pure vector search."""
        query_emb = [0.1] * 384
        
        result = await self.db.query(f"""
            SELECT *, vector::distance::knn() AS score
            FROM doc WHERE embedding <|{k}|> $emb
            ORDER BY score ASC
        """, {"emb": query_emb})
        
        return result[0] if result else []
    
    # ----- Full-Text Only -----
    
    async def text_search(self, query: str, k: int = 5) -> list:
        """Pure text search."""
        result = await self.db.query(f"""
            SELECT *, search::score() AS score
            FROM doc WHERE content @@ $query
            ORDER BY score DESC LIMIT {k}
        """, {"query": query})
        
        return result[0] if result else []


async def demo():
    """Demo."""
    agent = HybridSearchAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Index
    await agent.index_document(
        "AI Agents",
        "Building AI agents with memory...",
        ["ai", "agents"]
    )
    
    # Search
    results = await agent.hybrid_search("memory", k=5)
    print(f"Found: {len(results)}")


if __name__ == "__main__":
    asyncio.run(demo())