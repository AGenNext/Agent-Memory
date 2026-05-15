#!/usr/bin/env python3
"""
Sample Agent: Chunking Strategy

Based on blog: "What chunking strategies exist and how to choose one?"
"""

import asyncio
from surrealdb import Surreal


class ChunkingAgent:
    """Document chunking agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "chunks", "database": "documents"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Chunk schema."""
        schemas = [
            """
            DEFINE TABLE document SCHEMAFULL;
            DEFINE FIELD title ON document TYPE string;
            DEFINE FIELD content ON document TYPE string;
            """,
            """
            DEFINE TABLE chunk SCHEMAFULL;
            DEFINE FIELD document ON chunk TYPE record(document);
            DEFINE FIELD content ON chunk TYPE string;
            DEFINE FIELD index ON chunk TYPE int;
            DEFINE FIELD embedding ON chunk TYPE array<float>;
            DEFINE FIELD strategy ON chunk TYPE string;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Chunking schema created")
    
    # ----- Chunking Strategies -----
    
    def fixed_chunk(self, text: str, size: int = 500, overlap: int = 50) -> list:
        """Fixed size chunking."""
        chunks = []
        for i in range(0, len(text), size - overlap:
            chunk = text[i:i+size]
            if chunk:
                chunks.append(chunk)
        return chunks
    
    def sentence_chunk(self, text: str, max_sentences: int = 5) -> list:
        """Split by sentences."""
        import re
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current = ""
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if current.count('.') < max_sentences:
                current += sent + ". "
            else:
                chunks.append(current.strip())
                current = sent + ". "
        
        if current:
            chunks.append(current.strip())
        
        return chunks
    
    def paragraph_chunk(self, text: str) -> list:
        """Split by paragraphs."""
        return [p.strip() for p in text.split("\n\n") if p.strip()]
    
    def recursive_chunk(self, text: str, delimiters: list = None) -> list:
        """Recursive chunking with multiple delimiters."""
        if not delimiters:
            delimiters = ["\n\n", "\n", ". ", " "]
        
        for delim in delimiters:
            if delim in text:
                parts = text.split(delim)
                if len(parts) > 1:
                    return [p.strip() for p in parts if p.strip()]
        
        return [text]
    
    # ----- Store Chunks -----
    
    async def ingest(self, title: str, content: str, 
                  strategy: str = "fixed", chunk_size: int = 500) -> list:
        """Ingest document with chunks."""
        # Create document
        doc = await self.db.query(
            "CREATE document SET title=$title, content=$content",
            {"title": title, "content": content}
        )
        doc_id = doc[0][0]["id"]
        
        # Chunk based on strategy
        if strategy == "fixed":
            chunks = self.fixed_chunk(content, chunk_size)
        elif strategy == "sentence":
            chunks = self.sentence_chunk(content)
        elif strategy == "paragraph":
            chunks = self.paragraph_chunk(content)
        else:
            chunks = self.recursive_chunk(content)
        
        # Store chunks
        results = []
        for i, chunk_text in enumerate(chunks):
            result = await self.db.query(
                """CREATE chunk SET document=$doc, content=$content, 
                index=$idx, strategy=$strategy""",
                {"doc": doc_id, "content": chunk_text, "idx": i, "strategy": strategy}
            )
            results.append(result[0][0])
        
        return results
    
    # ----- Query Chunks -----
    
    async def search(self, query: str, k: int = 5) -> list:
        """Search chunks."""
        result = await self.db.query(
            f"""SELECT *, vector::distance::knn() AS score FROM chunk 
            WHERE embedding <|{k}|> $query
            ORDER BY score ASC""",
            {"query": [0.1] * 384}  # Placeholder
        )
        return result[0] if result else []


async def demo():
    """Demo."""
    agent = ChunkingAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Test fixed chunking
    text = "This is sentence one. This is sentence two. This is sentence three."
    chunks = agent.sentence_chunk(text, 2)
    print(f"Chunks: {chunks}")


if __name__ == "__main__":
    asyncio.run(demo())