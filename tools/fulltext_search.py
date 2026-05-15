#!/usr/bin/env python3
"""
Tool: Full-Text Search

Search with analyzers and scoring.
"""

import asyncio
from surrealdb import Surreal


class FullTextSearchTool:
    """Full-text search tool."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "search", "database": "text"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- Analyzer -----
    
    async def create_analyzer(self, name: str, tokenizer: str = "basic",
                         filters: list = None):
        """Create text analyzer."""
        filters_sql = ""
        if filters:
            filters_sql = f", FILTERS {', '.join(filters)}"
        
        await self.db.query(f"""
            DEFINE ANALYZER {name} TOKENIZER {tokenizer}{filters_sql}
        """)
        print(f"✅ Analyzer: {name}")
    
    # ----- Index -----
    
    async def create_index(self, table: str, field: str, 
                      analyzer: str = "en", index_type: str = "SEARCH"):
        """Create full-text index."""
        if index_type == "SEARCH":
            await self.db.query(f"""
                DEFINE INDEX {table}_{field} ON {table}
                FIELDS {field} SEARCH ANALYZER {analyzer} BM25
            """)
        else:
            await self.db.query(f"""
                DEFINE INDEX {table}_{field} ON {table}
                FIELDS {field} {index_type}
            """)
        print(f"✅ Index: {table}_{field}")
    
    # ----- Search -----
    
    async def search(self, table: str, query: str, 
                  limit: int = 10) -> list:
        """Full-text search."""
        result = await self.db.query(f"""
            SELECT *, 
                search::score() AS score
            FROM {table}
            WHERE {table}.* @@ $query
            ORDER BY score DESC
            LIMIT {limit}
        """, {"query": query})
        
        return result[0] if result else []
    
    async def search_field(self, table: str, field: str, query: str,
                      limit: int = 10) -> list:
        """Search specific field."""
        result = await self.db.query(f"""
            SELECT *, search::score() AS score
            FROM {table}
            WHERE {field} @@ $query
            ORDER BY score DESC
            LIMIT {limit}
        """, {"query": query})
        
        return result[0] if result else []
    
    async def bm25(self, table: str, query: str, 
                  limit: int = 10) -> list:
        """BM25 ranking."""
        result = await self.db.query(f"""
            SELECT *, 
                search::score(1.2, 0.75) AS bm25
            FROM {table}
            WHERE {table}.* @@ $query
            ORDER BY bm25 DESC
            LIMIT {limit}
        """, {"query": query})
        
        return result[0] if result else []
    
    # ----- Highlight -----
    
    async def highlight(self, table: str, field: str, query: str) -> list:
        """Highlight matches."""
        result = await self.db.query(f"""
            SELECT *, search::highlight($query) AS highlight
            FROM {table}
            WHERE {field} @@ $query
        """, {"query": query})
        
        return result[0] if result else []


async def demo():
    """Demo."""
    fts = FullTextSearchTool()
    await fts.connect()
    
    await fts.create_analyzer("my_analyzer", "basic", ["lowercase", "ascii"])
    await fts.create_index("article", "content", "my_analyzer")
    
    results = await fts.search("article", "artificial intelligence", k=5)
    print(f"Found: {len(results)}")


if __name__ == "__main__":
    asyncio.run(demo())