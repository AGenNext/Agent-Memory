"""
Agent-Memory · Pydantic models

Design:
  Spectron  → 6 categories, tri-temporal, provenance, calibration, supersession
  A-Mem     → keywords/tags/evolved_at for memory evolution
  Spacebot  → WorkingMemory (Cortex layers)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MemoryCategory(str, Enum):
    """Spectron six typed memory categories."""
    EPISODIC     = "episodic"      # raw conversational record
    IDENTITY     = "identity"      # durable facts about agent/user
    KNOWLEDGE    = "knowledge"     # learnt things; decays without reinforcement
    CONTEXT      = "context"       # active working context, short-lived
    INSTRUCTION  = "instruction"   # behavioural directives for prompt assembly
    UNCERTAINTY  = "uncertainty"   # explicit "we don't know yet" rows


class SourceKind(str, Enum):
    """Provenance source kinds (Spectron)."""
    AGENT_TURN    = "agent_turn"
    USER_TURN     = "user_turn"
    DOCUMENT      = "document"
    REFLECTION    = "reflection"
    ELABORATION   = "elaboration"
    CONSOLIDATION = "consolidation"
    TOOL_OUTPUT   = "tool_output"
    EXTERNAL      = "external"


class MemoryScope(str, Enum):
    AGENT   = "agent"
    TEAM    = "team"
    ORG     = "org"
    PROJECT = "project"


class EdgeKind(str, Enum):
    """Graph edge types (Spectron + Spacebot)."""
    RELATED_TO  = "related_to"
    UPDATES     = "updates"
    CONTRADICTS = "contradicts"
    CAUSED_BY   = "caused_by"
    PART_OF     = "part_of"


class DecisionStatus(str, Enum):
    PENDING  = "pending"
    SUCCESS  = "success"
    FAILED   = "failed"
    REJECTED = "rejected"


class WorkingMemoryLayer(str, Enum):
    """Spacebot Cortex five layers."""
    IDENTITY_CONTEXT  = "identity_context"
    INTRADAY_SYNTHESIS = "intraday_synthesis"
    DAILY_ROLLUP      = "daily_rollup"
    CROSS_AGENT_MAP   = "cross_agent_map"
    KNOWLEDGE_BRIEF   = "knowledge_brief"


class EvolutionStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DONE       = "done"
    SKIPPED    = "skipped"


class RetrievalTier(int, Enum):
    """Spectron four-tier query ladder."""
    DIRECT_LOOKUP  = 1   # typed lookup by key — sub-ms
    RESPONSE_REUSE = 2   # cache with entity-aware invalidation
    HYBRID         = 3   # vector + BM25 + graph + trace-derived features
    FULL_CONTEXT   = 4   # broader sweep with HyDE rewrite


# ---------------------------------------------------------------------------
# Memory record
# ---------------------------------------------------------------------------

class MemoryRecord(BaseModel):
    """Core memory unit with Spectron fields."""

    # Identification
    id: str | None = None

    # Category & content
    category: MemoryCategory
    content: str
    summary: str | None = None

    # Scope & ownership
    agent_id: str
    session_id: str | None = None
    scope: MemoryScope = MemoryScope.AGENT

    # Tri-temporal (Spectron)
    known_time: datetime | None = None           # set by DB VALUE time::now()
    valid_time_start: datetime | None = None     # when assertion holds in world
    valid_time_end: datetime | None = None       # None = currently valid

    # Provenance (Spectron)
    source_kind: SourceKind = SourceKind.AGENT_TURN
    source_ref: str | None = None                # turn_id / doc_id
    source_trust: float = Field(default=0.7, ge=0.0, le=1.0)
    derived_from: list[str] | None = None        # record IDs

    # Calibration (Spectron)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)

    # Supersession (Spectron: supersede-not-overwrite)
    superseded: bool = False
    superseded_at: datetime | None = None
    superseded_by: str | None = None             # record ID of replacement

    # A-Mem evolution
    keywords: list[str] | None = None
    tags: list[str] | None = None
    evolved_at: datetime | None = None

    # Vector embedding
    embedding: list[float] | None = None

    created_at: datetime | None = None
    updated_at: datetime | None = None


class MemoryCreate(BaseModel):
    """Input for creating a new memory (no id/timestamps)."""
    category: MemoryCategory
    content: str
    summary: str | None = None
    agent_id: str
    session_id: str | None = None
    scope: MemoryScope = MemoryScope.AGENT
    valid_time_start: datetime | None = None
    valid_time_end: datetime | None = None
    source_kind: SourceKind = SourceKind.AGENT_TURN
    source_ref: str | None = None
    source_trust: float = Field(default=0.7, ge=0.0, le=1.0)
    derived_from: list[str] | None = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    keywords: list[str] | None = None
    tags: list[str] | None = None
    embedding: list[float] | None = None


class SupersedeRequest(BaseModel):
    """Supersede an existing memory with a new one."""
    old_memory_id: str
    new_content: str
    new_source_kind: SourceKind = SourceKind.AGENT_TURN
    new_source_ref: str | None = None
    new_confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    new_embedding: list[float] | None = None


# ---------------------------------------------------------------------------
# Graph edge
# ---------------------------------------------------------------------------

class MemoryEdge(BaseModel):
    id: str | None = None
    source_id: str       # memory record ID
    target_id: str       # memory record ID
    kind: EdgeKind
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Retrieval trace
# ---------------------------------------------------------------------------

class RetrievalTrace(BaseModel):
    """Spectron: traces are first-class memory; ranker reads its own history."""
    id: str | None = None
    agent_id: str
    session_id: str | None = None
    query_text: str
    query_embedding: list[float] | None = None
    tier: RetrievalTier = RetrievalTier.HYBRID
    result_ids: list[str] = Field(default_factory=list)
    result_scores: list[float] | None = None
    useful: bool | None = None      # feedback signal
    correction: bool | None = None  # was this result corrected?
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Decision trace
# ---------------------------------------------------------------------------

class DecisionTrace(BaseModel):
    id: str | None = None
    run_id: str
    step_id: str
    agent_id: str
    actor: str | None = None
    action: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    status: DecisionStatus
    memory_refs: list[str] | None = None  # memory IDs used in this decision
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Working memory  (Spacebot Cortex)
# ---------------------------------------------------------------------------

class WorkingMemory(BaseModel):
    """Background-synthesised context layers — never written per LLM call."""
    id: str | None = None
    agent_id: str
    layer: WorkingMemoryLayer
    content: str
    source_memories: list[str] | None = None
    valid_date: datetime | None = None   # for daily_rollup — which day
    token_count: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Evolution queue  (A-Mem)
# ---------------------------------------------------------------------------

class EvolutionJob(BaseModel):
    """Queued job to evolve related memories after a new memory is created."""
    id: str | None = None
    new_memory_id: str
    agent_id: str
    category: MemoryCategory
    status: EvolutionStatus = EvolutionStatus.PENDING
    processed_at: datetime | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Query / retrieval contracts
# ---------------------------------------------------------------------------

class MemoryQuery(BaseModel):
    """Input for hybrid memory retrieval."""
    agent_id: str
    query_text: str
    query_embedding: list[float] | None = None
    categories: list[MemoryCategory] | None = None
    scope: MemoryScope | None = None
    session_id: str | None = None
    include_superseded: bool = False
    tier: RetrievalTier = RetrievalTier.HYBRID
    top_k: int = Field(default=10, ge=1, le=100)
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    # Temporal filters
    valid_at: datetime | None = None   # only memories valid at this time
    known_after: datetime | None = None


class MemoryQueryResult(BaseModel):
    memories: list[MemoryRecord]
    trace_id: str | None = None
    tier_used: RetrievalTier = RetrievalTier.HYBRID
    total_candidates: int = 0
