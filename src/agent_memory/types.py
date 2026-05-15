"""Type definitions for Agent Memory SDK."""

from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class DecisionStep(BaseModel):
    """A single decision step in agent reasoning."""
    id: str
    session: str
    action: str
    tool: str | None = None
    tool_args: dict[str, Any] | None = None
    result_summary: str | None = None
    created: datetime | None = None


class RetrievalTrace(BaseModel):
    """A retrieval trace for auditing."""
    id: str
    session: str
    method: Literal["vector", "graph", "hybrid"]
    query_text: str
    entity_ids: list[str] = Field(default_factory=list)
    distances: list[float] = Field(default_factory=list)
    created: datetime | None = None


class ResponseTrace(BaseModel):
    """A response trace for past lookup."""
    id: str
    session: str
    query: str
    response: str
    model: str
    token_count: int | None = None
    created: datetime | None = None


class Knowledge(BaseModel):
    """A knowledge fact."""
    id: str
    fact: str
    category: str | None = None
    source: str | None = None
    verified: bool = False
    created: datetime | None = None


class Article(BaseModel):
    """KB article with embedding."""
    id: str
    title: str
    category: str
    content: str
    embedding: list[float] = Field(default_factory=list)
    created: datetime | None = None


class Product(BaseModel):
    """Product entity."""
    id: str
    name: str
    description: str | None = None
    version: str | None = None


class Ticket(BaseModel):
    """Support ticket."""
    id: str
    subject: str
    description: str | None = None
    status: str = "open"
    priority: str = "medium"
    created: datetime | None = None


class Solution(BaseModel):
    """Solution/resolution."""
    id: str
    title: str
    steps: str
    verified: bool = False
    weight: float = 1.0


class User(BaseModel):
    """End user."""
    id: str
    name: str
    email: str | None = None
    role: str = "user"
    created: datetime | None = None


class Tenant(BaseModel):
    """Multi-tenant organization."""
    id: str
    name: str
    slug: str
    plan: str = "free"
    status: str = "active"
    created: datetime | None = None


class Job(BaseModel):
    """Background job."""
    id: str
    name: str
    status: str = "queued"
    progress: int = 0
    result: dict[str, Any] | None = None
    error: str | None = None
    attempts: int = 0
    created: datetime | None = None