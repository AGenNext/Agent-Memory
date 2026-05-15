"""Configuration for Agent Memory SDK."""

from typing import Literal
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM provider configuration."""
    provider: Literal["openai", "anthropic", "ollama"] = "openai"
    model: str = "gpt-4o"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096


class EmbeddingConfig(BaseModel):
    """Embedding model configuration."""
    provider: Literal["openai", "cohere"] = "openai"
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    api_key: str | None = None


class Config(BaseModel):
    """Main configuration for Agent Memory."""
    
    # Database
    db_url: str = "ws://localhost:8000/rpc"
    db_user: str = "root"
    db_pass: str = "root"
    db_namespace: str = "memory"
    db_database: str = "agent"
    
    # LLM
    llm: LLMConfig = Field(default_factory=LLMConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    
    # Agent behavior
    max_rounds: int = 15
    enable_trace: bool = True
    enable_decision_review: bool = True
    enable_past_decisions: bool = True
    
    # Tools
    enable_search: bool = True
    enable_find_related: bool = True
    enable_find_solutions: bool = True
    
    class Config:
        frozen = True