"""
Agent-Memory · MemoryService

High-level service layer on top of SurrealMemoryClient.

Implements three background services:
  Reconciler     — Spectron: supersede-not-overwrite, calibration, contradiction detection
  EvolutionWorker — A-Mem: drain evolution queue, update related memory context/tags
  CortexSynthesiser — Spacebot: background synthesis of working_memory layers
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from agent_memory.backends.surrealdb.client import SurrealMemoryClient
from agent_memory.models import (
    DecisionStatus,
    DecisionTrace,
    EdgeKind,
    MemoryCategory,
    MemoryCreate,
    MemoryQuery,
    MemoryQueryResult,
    MemoryRecord,
    RetrievalTier,
    SourceKind,
    SupersedeRequest,
    WorkingMemory,
    WorkingMemoryLayer,
)

log = logging.getLogger(__name__)


class MemoryService:
    """
    Orchestrates all memory operations for Agent-Memory.

    Usage:
        svc = MemoryService(client)
        mem = await svc.remember(agent_id, content, category=MemoryCategory.KNOWLEDGE)
        results = await svc.recall(agent_id, "what does the user prefer?")
    """

    def __init__(self, client: SurrealMemoryClient) -> None:
        self.db = client

    # ------------------------------------------------------------------
    # Core API — write
    # ------------------------------------------------------------------

    async def remember(
        self,
        agent_id: str,
        content: str,
        category: MemoryCategory = MemoryCategory.KNOWLEDGE,
        session_id: str | None = None,
        source_kind: SourceKind = SourceKind.AGENT_TURN,
        source_ref: str | None = None,
        source_trust: float = 0.7,
        confidence: float = 0.8,
        importance: float = 0.5,
        keywords: list[str] | None = None,
        tags: list[str] | None = None,
        embedding: list[float] | None = None,
        valid_time_start: datetime | None = None,
        valid_time_end: datetime | None = None,
    ) -> MemoryRecord:
        """
        Create a new memory.
        SurrealDB DEFINE EVENT fires an evolution_queue job automatically.
        """
        payload = MemoryCreate(
            agent_id=agent_id,
            content=content,
            category=category,
            session_id=session_id,
            source_kind=source_kind,
            source_ref=source_ref,
            source_trust=source_trust,
            confidence=confidence,
            importance=importance,
            keywords=keywords,
            tags=tags,
            embedding=embedding,
            valid_time_start=valid_time_start,
            valid_time_end=valid_time_end,
        )
        mem = await self.db.create_memory(payload)
        log.debug("created memory %s (%s) for agent %s", mem.id, category.value, agent_id)
        return mem

    async def update(
        self,
        old_memory_id: str,
        new_content: str,
        new_source_kind: SourceKind = SourceKind.AGENT_TURN,
        new_source_ref: str | None = None,
        new_confidence: float = 0.8,
        new_embedding: list[float] | None = None,
    ) -> tuple[MemoryRecord, MemoryRecord]:
        """
        Spectron: supersede-not-overwrite.
        Returns (superseded_old, new_memory).
        """
        req = SupersedeRequest(
            old_memory_id=old_memory_id,
            new_content=new_content,
            new_source_kind=new_source_kind,
            new_source_ref=new_source_ref,
            new_confidence=new_confidence,
            new_embedding=new_embedding,
        )
        old, new = await self.db.supersede_memory(req)
        log.debug("superseded %s → %s", old_memory_id, new.id)
        return old, new

    async def forget(self, memory_id: str, purge: bool = False) -> None:
        """
        Spectron: forget is an explicit verb.
        Default: marks superseded with valid_time_end = now (queryable history kept).
        purge=True: hard DELETE (use only for GDPR/legal obligations).
        """
        if purge:
            await self.db.query("DELETE type::thing('memory', $id);", {"id": memory_id.split(":")[-1]})
            log.info("PURGED memory %s", memory_id)
        else:
            await self.db.query(
                """
                UPDATE type::thing('memory', $id) SET
                    superseded     = true,
                    superseded_at  = time::now(),
                    valid_time_end = time::now(),
                    updated_at     = time::now();
                """,
                {"id": memory_id.split(":")[-1]},
            )
            log.debug("forgot (soft) memory %s", memory_id)

    # ------------------------------------------------------------------
    # Core API — read
    # ------------------------------------------------------------------

    async def recall(
        self,
        agent_id: str,
        query_text: str,
        query_embedding: list[float] | None = None,
        categories: list[MemoryCategory] | None = None,
        top_k: int = 10,
        tier: RetrievalTier = RetrievalTier.HYBRID,
        session_id: str | None = None,
        min_confidence: float = 0.0,
        valid_at: datetime | None = None,
    ) -> MemoryQueryResult:
        """
        Hybrid retrieval with automatic trace recording.
        """
        q = MemoryQuery(
            agent_id=agent_id,
            query_text=query_text,
            query_embedding=query_embedding,
            categories=categories,
            top_k=top_k,
            tier=tier,
            session_id=session_id,
            min_confidence=min_confidence,
            valid_at=valid_at,
        )
        return await self.db.query_memories(q)

    async def get_context(self, agent_id: str) -> list[WorkingMemory]:
        """
        Return the assembled Cortex working memory for prompt injection.
        Order: identity → intraday → cross_agent → knowledge_brief
        (context layer is not in working_memory — it's in the active session)
        """
        return await self.db.get_working_memory(agent_id, layers=[
            WorkingMemoryLayer.IDENTITY_CONTEXT,
            WorkingMemoryLayer.INTRADAY_SYNTHESIS,
            WorkingMemoryLayer.CROSS_AGENT_MAP,
            WorkingMemoryLayer.KNOWLEDGE_BRIEF,
        ])

    async def get_history(self, memory_id: str) -> list[MemoryRecord]:
        """Spectron: walk the supersession lineage for a memory."""
        return await self.db.supersession_lineage(memory_id)

    # ------------------------------------------------------------------
    # Decision trace
    # ------------------------------------------------------------------

    async def trace_decision(
        self,
        run_id: str,
        step_id: str,
        agent_id: str,
        action: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        status: DecisionStatus = DecisionStatus.SUCCESS,
        memory_refs: list[str] | None = None,
        actor: str | None = None,
    ) -> DecisionTrace:
        dt = DecisionTrace(
            run_id=run_id,
            step_id=step_id,
            agent_id=agent_id,
            actor=actor,
            action=action,
            input=input_data,
            output=output_data,
            status=status,
            memory_refs=memory_refs,
        )
        return await self.db.create_decision_trace(dt)

    # ------------------------------------------------------------------
    # Reconciler  (Spectron calibration + contradiction detection)
    # ------------------------------------------------------------------

    async def reconcile(
        self,
        agent_id: str,
        new_memory_id: str,
        related_ids: list[str],
    ) -> None:
        """
        Check new memory against related memories for contradictions.
        If confidence floor not met, emit uncertainty row.
        This is called by the EvolutionWorker after link generation.
        """
        CONFIDENCE_FLOOR = 0.4

        new_raw = await self.db.select(new_memory_id)
        if not new_raw:
            return
        new_mem = MemoryRecord(**new_raw)

        for related_id in related_ids:
            related_raw = await self.db.select(related_id)
            if not related_raw:
                continue
            related = MemoryRecord(**related_raw)

            # Trust-based supersession guard (Spectron calibration):
            # Low-confidence new memory MUST NOT supersede high-confidence existing one
            if (
                new_mem.confidence < CONFIDENCE_FLOOR
                and related.confidence > new_mem.confidence
            ):
                # Emit uncertainty row instead
                await self.remember(
                    agent_id=agent_id,
                    content=(
                        f"Uncertainty: new memory (id={new_memory_id}) "
                        f"conflicts with existing (id={related_id}) but "
                        f"confidence {new_mem.confidence:.2f} is below floor {CONFIDENCE_FLOOR}."
                    ),
                    category=MemoryCategory.UNCERTAINTY,
                    source_kind=SourceKind.CONSOLIDATION,
                    confidence=new_mem.confidence,
                    importance=0.6,
                )
                log.warning(
                    "reconciler emitted uncertainty for %s vs %s",
                    new_memory_id,
                    related_id,
                )
                continue

            # Contradiction detection (simple heuristic — extend with LLM judge if needed)
            await self.db.relate_memories(
                source_id=new_memory_id,
                target_id=related_id,
                kind=EdgeKind.RELATED_TO,
                weight=0.8,
            )


# ---------------------------------------------------------------------------
# Evolution Worker  (A-Mem: drain queue, evolve related memories)
# ---------------------------------------------------------------------------

class EvolutionWorker:
    """
    Background worker — drains the evolution_queue and updates
    context/keywords/tags of related memories.

    In production: run as an async task on a configurable interval.
    Does NOT call LLM directly — the caller injects an evolve_fn
    (can be an LLM call or a simple rule-based function).
    """

    def __init__(
        self,
        client: SurrealMemoryClient,
        service: MemoryService,
        evolve_fn: Any | None = None,
    ) -> None:
        self.db = client
        self.svc = service
        # evolve_fn(new_memory: MemoryRecord, related: list[MemoryRecord])
        #   -> list[dict] of {id, keywords, tags, summary} updates
        self.evolve_fn = evolve_fn

    async def run_once(self, agent_id: str, batch_size: int = 10) -> int:
        """Process one batch. Returns number of jobs processed."""
        jobs = await self.db.pop_evolution_jobs(agent_id, limit=batch_size)
        if not jobs:
            return 0

        processed = 0
        for job in jobs:
            try:
                new_raw = await self.db.select(str(job.new_memory_id))
                if not new_raw:
                    await self.db.skip_evolution_job(str(job.id))
                    continue

                new_mem = MemoryRecord(**new_raw)

                # Find top-k related memories by vector similarity
                result = await self.svc.recall(
                    agent_id=agent_id,
                    query_text=new_mem.content,
                    query_embedding=new_mem.embedding,
                    top_k=5,
                    tier=RetrievalTier.HYBRID,
                )
                related = [m for m in result.memories if m.id != str(job.new_memory_id)]

                # Run reconciler
                await self.svc.reconcile(
                    agent_id=agent_id,
                    new_memory_id=str(job.new_memory_id),
                    related_ids=[m.id for m in related if m.id],
                )

                # A-Mem evolution: update context of related memories
                if self.evolve_fn and related:
                    updates = await self.evolve_fn(new_mem, related)
                    for upd in updates:
                        mem_id = upd.pop("id", None)
                        if mem_id and upd:
                            upd["evolved_at"] = datetime.now(timezone.utc).isoformat()
                            await self.db.query(
                                "UPDATE type::thing('memory', $id) MERGE $data;",
                                {"id": mem_id.split(":")[-1], "data": upd},
                            )

                await self.db.complete_evolution_job(str(job.id))
                processed += 1

            except Exception as exc:
                log.error("evolution job %s failed: %s", job.id, exc)
                await self.db.skip_evolution_job(str(job.id))

        log.debug("evolution worker processed %d jobs for agent %s", processed, agent_id)
        return processed


# ---------------------------------------------------------------------------
# Cortex Synthesiser  (Spacebot Cortex pattern)
# ---------------------------------------------------------------------------

class CortexSynthesiser:
    """
    Background process that maintains working_memory layers.
    Never called per LLM turn — runs on schedule or on graph-change events.

    synthesise_fn: callable(layer, source_memories, agent_id) -> str
      In production this is an LLM call with a cheap/fast model.
      Can also be a rule-based compressor for intraday_synthesis.
    """

    def __init__(
        self,
        client: SurrealMemoryClient,
        service: MemoryService,
        synthesise_fn: Any,
    ) -> None:
        self.db = client
        self.svc = service
        self.synthesise_fn = synthesise_fn

    async def refresh_intraday(self, agent_id: str, session_id: str | None = None) -> WorkingMemory:
        """
        Compress today's episodic memories into a narrative.
        Replaces the existing intraday_synthesis layer.
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await self.svc.recall(
            agent_id=agent_id,
            query_text="",  # no filter — get all today's memories
            categories=[MemoryCategory.EPISODIC, MemoryCategory.KNOWLEDGE],
            top_k=50,
            tier=RetrievalTier.DIRECT_LOOKUP,
            valid_at=datetime.now(timezone.utc),
            session_id=session_id,
        )
        recent = [m for m in result.memories if m.known_time and m.known_time >= today_start]

        content = await self.synthesise_fn(
            WorkingMemoryLayer.INTRADAY_SYNTHESIS,
            recent,
            agent_id,
        )

        wm = WorkingMemory(
            agent_id=agent_id,
            layer=WorkingMemoryLayer.INTRADAY_SYNTHESIS,
            content=content,
            source_memories=[m.id for m in recent if m.id],
            token_count=len(content.split()),
        )
        return await self.db.upsert_working_memory(wm)

    async def refresh_daily_rollup(self, agent_id: str, date: datetime) -> WorkingMemory:
        """Midnight job: compress intraday into daily summary."""
        existing = await self.db.get_working_memory(
            agent_id, [WorkingMemoryLayer.INTRADAY_SYNTHESIS]
        )
        source_content = existing[0].content if existing else ""

        content = await self.synthesise_fn(
            WorkingMemoryLayer.DAILY_ROLLUP,
            source_content,
            agent_id,
        )

        wm = WorkingMemory(
            agent_id=agent_id,
            layer=WorkingMemoryLayer.DAILY_ROLLUP,
            content=content,
            valid_date=date,
            token_count=len(content.split()),
        )
        return await self.db.upsert_working_memory(wm)

    async def refresh_knowledge_brief(self, agent_id: str) -> WorkingMemory:
        """
        Change-driven: regenerate when memory graph changes.
        Synthesises identity + knowledge memories into a briefing.
        """
        result = await self.svc.recall(
            agent_id=agent_id,
            query_text="",
            categories=[MemoryCategory.IDENTITY, MemoryCategory.KNOWLEDGE],
            top_k=30,
            tier=RetrievalTier.DIRECT_LOOKUP,
        )

        content = await self.synthesise_fn(
            WorkingMemoryLayer.KNOWLEDGE_BRIEF,
            result.memories,
            agent_id,
        )

        wm = WorkingMemory(
            agent_id=agent_id,
            layer=WorkingMemoryLayer.KNOWLEDGE_BRIEF,
            content=content,
            source_memories=[m.id for m in result.memories if m.id],
            token_count=len(content.split()),
        )
        return await self.db.upsert_working_memory(wm)
