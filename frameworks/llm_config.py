"""
LLM Configuration - Switch between providers easily

Usage:
    from frameworks.llm_config import get_llm, LLMProvider
    
    # Use OpenAI
    llm = get_llm(LLMProvider.OPENAI, model="gpt-4o")
    
    # Use Anthropic
    llm = get_llm(LLMProvider.ANTHROPIC, model="claude-3-opus")
    
    # Use Ollama (local)
    llm = get_llm(LLMProvider.OLLAMA, model="llama3")
    
    # Use Groq
    llm = get_llm(LLMProvider.GROQ, model="llama-3-70b")
"""

import os
from enum import Enum
from typing import Optional, Protocol, Any
import json


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GROQ = "groq"
    GOOGLE = "google"
    MISTRAL = "mistral"
    COHERE = "cohere"


class LLMConfig:
    """LLM Configuration"""
    
    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OPENAI,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv(f"{provider.value.upper()}_API_KEY")
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def to_dict(self) -> dict:
        return {
            "provider": self.provider.value,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


class LLM(Protocol):
    """LLM Protocol"""
    
    async def complete(self, prompt: str) -> str:
        """Generate completion"""
        ...
    
    async def embed(self, text: str) -> list[float]:
        """Generate embeddings"""
        ...


class OpenAILLM:
    """OpenAI LLM"""
    
    def __init__(self, config: LLMConfig):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=config.api_key or os.getenv("OPENAI_API_KEY"),
            base_url=config.base_url,
        )
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    async def complete(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content
    
    async def embed(self, text: str) -> list[float]:
        response = await self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding


class AnthropicLLM:
    """Anthropic Claude LLM"""
    
    def __init__(self, config: LLMConfig):
        from anthropic import AsyncAnthropic
        self.client = AsyncAnthropic(
            api_key=config.api_key or os.getenv("ANTHROPIC_API_KEY"),
            base_url=config.base_url,
        )
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    async def complete(self, prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    
    async def embed(self, text: str) -> list[float]:
        # Note: Anthropic doesn't have embeddings, use alternative
        raise NotImplementedError("Anthropic doesn't support embeddings")


class OllamaLLM:
    """Ollama local LLM"""
    
    def __init__(self, config: LLMConfig):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key="ollama",  # Dummy
            base_url=config.base_url or "http://localhost:11434/v1",
        )
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    async def complete(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content
    
    async def embed(self, text: str) -> list[float]:
        # Ollama embeddings
        import httpx
        response = await httpx.AsyncClient().post(
            f"{self.client.base_url}/embeddings",
            json={"model": "nomic-embed-text", "prompt": text},
        )
        return response.json()["embedding"]


class GroqLLM:
    """Groq LLM (fast inference)"""
    
    def __init__(self, config: LLMConfig):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(
            api_key=config.api_key or os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = config.model
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    async def complete(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return response.choices[0].message.content
    
    async def embed(self, text: str) -> list[float]:
        # Use a separate embeddings provider
        raise NotImplementedError("Use OpenAI for embeddings with Groq")


class GoogleLLM:
    """Google Gemini LLM"""
    
    def __init__(self, config: LLMConfig):
        import google.generativeai as genai
        genai.configure(api_key=config.api_key or os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel(config.model)
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens
    
    async def complete(self, prompt: str) -> str:
        response = await self.model.generate_content_async(
            prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
        )
        return response.text
    
    async def embed(self, text: str) -> list[float]:
        result = genai.embed_content(
            model="embedding-001",
            content=text,
        )
        return result["embedding"]


def get_llm(
    provider: LLMProvider,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> LLM:
    """
    Get LLM instance by provider.
    
    Example:
        llm = get_llm(LLMProvider.OPENAI, model="gpt-4o")
        llm = get_llm(LLMProvider.OLLAMA, model="llama3", base_url="http://localhost:11434")
    """
    config = LLMConfig(
        provider=provider,
        model=model or get_default_model(provider),
        api_key=api_key,
        base_url=base_url,
        **kwargs
    )
    
    if provider == LLMProvider.OPENAI:
        return OpenAILLM(config)
    elif provider == LLMProvider.ANTHROPIC:
        return AnthropicLLM(config)
    elif provider == LLMProvider.OLLAMA:
        return OllamaLLM(config)
    elif provider == LLMProvider.GROQ:
        return GroqLLM(config)
    elif provider == LLMProvider.GOOGLE:
        return GoogleLLM(config)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def get_default_model(provider: LLMProvider) -> str:
    """Get default model for provider"""
    defaults = {
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.ANTHROPIC: "claude-3-haiku-20240307",
        LLMProvider.OLLAMA: "llama3",
        LLMProvider.GROQ: "llama-3-70b-versatile",
        LLMProvider.GOOGLE: "gemini-1.5-flash",
    }
    return defaults.get(provider, "gpt-4o-mini")


# Config presets
LLM_PRESETS = {
    "fast": LLMConfig(provider=LLMProvider.GROQ, model="llama-3-70b-versatile"),
    "smart": LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o"),
    "cheap": LLMConfig(provider=LLMProvider.OPENAI, model="gpt-4o-mini"),
    "local": LLMConfig(provider=LLMProvider.OLLAMA, model="llama3"),
    "claude": LLMConfig(provider=LLMProvider.ANTHROPIC, model="claude-3-haiku-20240307"),
}


# Example usage
if __name__ == "__main__":
    async def test():
        # Use preset
        llm = get_llm(**LLM_PRESETS["fast"].to_dict())
        
        # Or configure manually
        # llm = get_llm(LLMProvider.OPENAI, model="gpt-4o")
        # llm = get_llm(LLMProvider.OLLAMA, model="llama3", base_url="http://localhost:11434")
        
        try:
            result = await llm.complete("Hello! What are you?")
            print(f"Response: {result}")
        except Exception as e:
            print(f"Error (likely no API key): {e}")
    
    asyncio.run(test())