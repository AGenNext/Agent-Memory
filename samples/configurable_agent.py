#!/usr/bin/env python3
"""
SurrealDB Agent with LLM Configuration

Configurable for multiple LLM providers:
- OpenAI (GPT-4, GPT-4o, o1)
- Anthropic (Claude)
- Ollama (local models)
- Groq (fast inference)
- Azure OpenAI
"""

import asyncio
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class LLMProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GROQ = "groq"
    AZURE = "azure"


@dataclass
class LLMConfig:
    """LLM Configuration."""
    provider: LLMProvider
    model: str
    api_key: str = None
    base_url: str = None
    temperature: float = 0.7
    max_tokens: int = 2048
    
    @classmethod
    def from_env(cls, provider: str = None) -> "LLMConfig":
        """Load from environment."""
        provider = provider or os.getenv("LLM_PROVIDER", "openai")
        
        configs = {
            "openai": cls(
                LLMProvider.OPENAI,
                os.getenv("OPENAI_MODEL", "gpt-4o"),
                api_key=os.getenv("OPENAI_API_KEY"),
            ),
            "anthropic": cls(
                LLMProvider.ANTHROPIC,
                os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            ),
            "ollama": cls(
                LLMProvider.OLLAMA,
                os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_URL", "http://localhost:11434"),
            ),
            "groq": cls(
                LLMProvider.GROQ,
                os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
                api_key=os.getenv("GROQ_API_KEY"),
            ),
        }
        
        return configs.get(provider, configs["openai"])


class LLMClient:
    """Configurable LLM client."""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = None
    
    async def setup(self):
        """Setup LLM client."""
        if self.config.provider == LLMProvider.OPENAI:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=self.config.api_key)
        
        elif self.config.provider == LLMProvider.ANTHROPIC:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=self.config.api_key)
        
        elif self.config.provider == LLMProvider.OLLAMA:
            import httpx
            self.client = httpx.AsyncClient(base_url=self.config.base_url)
        
        elif self.config.provider == LLMProvider.GROQ:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
    
    async def chat(self, messages: List[Dict], stream: bool = False) -> str:
        """Chat with LLM."""
        
        if self.config.provider == LLMProvider.OPENAI:
            return await self._openai_chat(messages, stream)
        
        elif self.config.provider == LLMProvider.ANTHROPIC:
            return await self._anthropic_chat(messages)
        
        elif self.config.provider == LLMProvider.OLLAMA:
            return await self._ollama_chat(messages)
        
        elif self.config.provider == LLMProvider.GROQ:
            return await self._openai_chat(messages, stream)
        
        return "Error: Unknown provider"
    
    async def _openai_chat(self, messages: List[Dict], stream: bool) -> str:
        """OpenAI/Groq chat."""
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stream=stream,
        )
        
        if stream:
            return response
        return response.choices[0].message.content
    
    async def _anthropic_chat(self, messages: List[Dict]) -> str:
        """Anthropic chat."""
        # Convert to Anthropic format
        system = None
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
        
        claude_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in messages if m["role"] != "system"
        ]
        
        response = await self.client.messages.create(
            model=self.config.model,
            system=system,
            messages=claude_messages,
            max_tokens=self.config.max_tokens,
        )
        
        return response.content[0].text
    
    async def _ollama_chat(self, messages: List[Dict]) -> str:
        """Ollama chat."""
        response = await self.client.post(
            "/api/chat",
            json={
                "model": self.config.model,
                "messages": messages,
                "stream": False,
            }
        )
        return response.json()["message"]["content"]
    
    async def embed(self, text: str) -> List[float]:
        """Get embeddings."""
        
        if self.config.provider == LLMProvider.OPENAI:
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return response.data[0].embedding
        
        elif self.config.provider == LLMProvider.OLLAMA:
            response = await self.client.post(
                "/api/embeddings",
                json={"model": self.config.model, "prompt": text}
            )
            return response.json()["embedding"]
        
        # Fallback
        return [0.1] * 384


class SurrealDBLLMAgent:
    """SurrealDB agent with configurable LLM."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
        self.llm = None
    
    def configure_llm(self, config: LLMConfig):
        """Configure LLM."""
        self.llm = LLMClient(config)
        return self
    
    async def connect(self):
        """Connect."""
        from surrealdb import Surreal
        self.db = Surreal(self.url)
        await self.db.connect()
        
        if self.llm:
            await self.llm.setup()
        return self
    
    async def schema(self, table: str, fields: Dict):
        """DEFINE TABLE."""
        for field, ftype in fields.items():
            await self.db.query(f"DEFINE FIELD {field} ON {table} TYPE {ftype}")
        await self.db.query(f"DEFINE TABLE {table} SCHEMAFULL")
    
    async def create(self, table: str, data: Dict):
        """CREATE."""
        return await self.db.query(f"CREATE {table} SET $data", {"data": data})
    
    async def search(self, query: str, table: str = "doc", k: int = 5) -> List[Dict]:
        """Semantic search."""
        if self.llm:
            emb = await self.llm.embed(query)
            result = await self.db.query(
                f"""SELECT *, vector::distance::knn() AS score 
                FROM {table} WHERE embedding <|{k}|> $emb 
                ORDER BY score ASC""",
                {"emb": emb}
            )
            return result[0] if result else []
        return []
    
    async def chat(self, prompt: str, context: str = None) -> str:
        """Chat with context."""
        if self.llm:
            messages = []
            
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Use this context: {context}"
                })
            
            messages.append({"role": "user", "content": prompt})
            
            return await self.llm.chat(messages)
        
        return "LLM not configured"
    
    async def rag_chat(self, question: str, table: str = "doc") -> Dict:
        """RAG chat."""
        # 1. Search
        docs = await self.search(question, table)
        context = "\n\n".join([d.get("content", "") for d in docs[:3]])
        
        # 2. Generate
        answer = await self.chat(f"Based on: {context}\n\nQuestion: {question}")
        
        return {
            "question": question,
            "context": context,
            "answer": answer,
            "sources": docs[:3],
        }


# ----- Demo -----

async def demo():
    """Demo configurable LLM."""
    
    # Load config from env or defaults
    config = LLMConfig.from_env()
    print(f"🤖 Using: {config.provider.value} / {config.model}")
    
    # Create agent
    agent = SurrealDBLLMAgent()
    agent.configure_llm(config)
    await agent.connect()
    
    # Schema
    await agent.schema("document", {
        "content": "string",
        "embedding": "array<float>",
        "source": "string",
    })
    
    # Add docs
    await agent.create("document", {
        "content": "AI agents use memory to maintain context.",
        "source": "docs",
    })
    
    # RAG chat
    if config.api_key or config.provider == LLMProvider.OLLAMA:
        result = await agent.rag_chat("How do AI agents work?")
        print(f"\n🤖 {result['answer'][:200]}...")
    else:
        print("\n⚠️ No API key, skipping LLM chat")


if __name__ == "__main__":
    asyncio.run(demo())