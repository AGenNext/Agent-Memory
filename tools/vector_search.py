#!/usr/bin/env python3
"""
Tool: Vector Search

KNN and similarity search.
Reference: https://surrealdb.com/docs/surrealql/datamodel/vector
"""

import asyncio
from surrealdb import Surreal


class VectorSearchTool:
    """Vector search tool."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "vectors", "database": "search"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- Create Index -----
    
    async def create_index(self, table: str, field: str, 
                        dimension: int = 384,
                        distance: str = "COSINE"):
        """Create HNSW vector index."""
        await self.db.query(f"""
            DEFINE INDEX {table}_vec ON {table}
            FIELDS {field} HNSW
            DIMENSION {dimension}
            DISTANCE {distance}
        """)
        print(f"✅ Index created: {table}_{field}")
    
    async def create_index_full(self, name: str, table: str, field: str,
                            dimension: int = 384,
                            distance: str = "COSINE",
                            m: int = 16, efc: int = 100):
        """Create HNSW with tuning."""
        await self.db.query(f"""
            DEFINE INDEX {name} ON {table}
            FIELDS {field} HNSW
            DIMENSION {dimension}
            DISTANCE {distance}
            M {m}
            EFC {efc}
        """)
    
    # ----- Search -----
    
    async def knn(self, table: str, query_vector: list,
                 k: int = 5, field: str = "embedding") -> list:
        """KNN search."""
        result = await self.db.query(f"""
            SELECT *, vector::distance::knn() AS distance
            FROM {table}
            WHERE {field} <|{k}|> $query
            ORDER BY distance ASC
        """, {"query": query_vector})
        
        return result[0] if result else []
    
    async def similar(self, table: str, query_vector: list,
                    k: int = 5, threshold: float = 0.7) -> list:
        """Similarity search with threshold."""
        result = await self.db.query(f"""
            SELECT *, vector::distance::knn() AS distance
            FROM {table}
            WHERE embedding <|{k}|> $query
            AND vector::distance::knn() < {threshold}
        """, {"query": query_vector})
        
        return result[0] if result else []
    
    # ----- Hybrid Search -----
    
    async def hybrid(self, table: str, query_text: str, query_vector: list,
                  k: int = 5) -> list:
        """Hybrid search (text + vector)."""
        # Text search
        text_result = await self.db.query(f"""
            SELECT * FROM {table}
            WHERE content @@ $query
            SEARCH ANALYZER en BM25
            LIMIT {k}
        """, {"query": query_text})
        
        # Vector search  
        vec_result = await self.db.query(f"""
            SELECT *, vector::distance::knn() AS distance
            FROM {table}
            WHERE embedding <|{k}|> $query
        """, {"query": query_vector})
        
        # Combine with RRF
        combined = await self.db.query("""
            SELECT * FROM search::rrf([$text, $vec], 5, 20)
        """, {"text": text_result[0] if text_result else [], 
              "vec": vec_result[0] if vec_result else []})
        
        return combined[0] if combined else []
    
    # ----- Distance -----
    
    async def cosine_distance(self, v1: list, v2: list) -> float:
        """Cosine distance."""
        return await self.db.query(
            "RETURN vector::distance::cosine($v1, $v2)",
            {"v1": v1, "v2": v2}
        )
    
    async def euclidean_distance(self, v1: list, v2: list) -> float:
        """Euclidean distance."""
        return await self.db.query(
            "RETURN vector::distance::euclidean($v1, $v2)",
            {"v1": v1, "v2": v2}
        )
    
    async def inner_product(self, v1: list, v2: list) -> float:
        """Inner product."""
        return await self.db.query(
            "RETURN vector::distance::inner_product($v1, $v2)",
            {"v1": v1, "v2": v2}
        )


async def demo():
    """Demo."""
    vs = VectorSearchTool()
    await vs.connect()
    
    # Create index
    await vs.create_index("document", "embedding", 384)
    
    # Search
    query = [0.1] * 384
    results = await vs.knn("document", query, k=5)
    print(f"Found: {len(results)} results")


if __name__ == "__main__":
    asyncio.run(demo())