from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    type: str
    content: dict[str, Any]
    embedding: list[float] | None = None
    created_at: datetime | None = None


class GraphRelation(BaseModel):
    source: str
    target: str
    relation: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionTrace(BaseModel):
    run_id: str
    step_id: str
    actor: str | None = None
    action: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    status: str
