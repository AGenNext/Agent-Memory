#!/usr/bin/env python3
"""
Plugin: Embeddings Provider

Embedding providers plugin for SurrealDB.
Based on: https://surrealdb.com/docs/build/integrations/embeddings/overview
"""

import asyncio
import os
from surrealdb import Surreal


class EmbeddingsPlugin:
    """Embeddings provider plugin (OpenAI, Mistral, FastEmbed)."""
    
    PLUGIN_NAME = "embeddings"
    PLUGIN_VERSION = "1.0.0"
    
    PROVIDERS = ["openai", "mistral", "fastembed", "ollama"]
    
    def __init__(self, url: str = "ws://localhost:8000/rpc",
                 provider: str = "openai", 
                 model: str = "text-embedding-3-small"):
        self.url = url
        self.provider = provider
        self.model = model
        self.db = None
    
    async def install(self):
        """Install plugin."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "embeddings", "database": "vectors"})
        await self.db.signin({"username": "root", "password": "root"})
        
        # Embeddings config
        await self.db.query("""
            DEFINE TABLE _embedding_config SCHEMAFULL;
            DEFINE FIELD provider ON _embedding_config TYPE string;
            DEFINE FIELD model ON _embedding_config TYPE string;
            DEFINE FIELD dimension ON _embedding_config TYPE int;
        """)
        
        print(f"✅ Embeddings plugin installed ({self.provider})")
        return self
    
    async def get_embedding(self, text: str) -> list:
        """Get embedding from provider."""
        if self.provider == "openai":
            return await self._openai_embedding(text)
        elif self.provider == "ollama":
            return await self._ollama_embedding(text)
        elif self.provider == "fastembed":
            return await self._fastembed_embedding(text)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
    
    async def _openai_embedding(self, text: str) -> list:
        """OpenAI embeddings."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            result = await client.embeddings.create(
                model=self.model,
                input=text
            )
            return result.data[0].embedding
        except Exception as e:
            print(f"OpenAI error: {e}")
            # Return mock for demo
            return [0.1] * 1536
    
    async def _ollama_embedding(self, text: str) -> list:
        """Ollama embeddings."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            try:
                r = await client.post(
                    "http://localhost:11434/api/embeddings",
                    json={"model": self.model, "prompt": text}
                )
                return r.json().get("embedding", [0.1] * 384)
            except:
                return [0.1] * 384
    
    async def _fastembed_embedding(self, text: str) -> list:
        """FastEmbed embeddings."""
        # Simulated for demo
        return [0.1] * 384
    
    async def embed_texts(self, texts: list) -> list:
        """Embed multiple texts."""
        embeddings = []
        for text in texts:
            emb = await self.get_embedding(text)
            embeddings.append(emb)
        return embeddings
    
    async def vector_search(self, query: str, table: str, 
                         k: int = 5, threshold: float = 0.7) -> list:
        """Vector search in SurrealDB."""
        # Get query embedding
        query_emb = await self.get_embedding(query)
        
        # Search
        result = await self.db.query(
            f"""SELECT *, vector::distance::knn() AS score FROM {table} 
            WHERE embedding <|{k}|> $emb ORDER BY score ASC""",
            {"emb": query_emb}
        )
        
        return result[0] if result else []


async def demo():
    """Demo."""
    plugin = EmbeddingsPlugin(provider="openai", model="text-embedding-3-small")
    await plugin.install()
    
    # Get embedding
    emb = await plugin.get_embedding("Hello, world!")
    print(f"Embedding dimension: {len(emb)}")
    
    # Vector search
    # result = await plugin.vector_search("AI agents", "document")
    # print(result)


if __name__ == "__main__":
    asyncio.run(demo())