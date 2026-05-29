"""
Agent-Memory · SurrealDB backend client

Implements:
  Spectron  → supersede, tri-temporal queries, retrieval traces, calibration
  A-Mem     → evolution queue drain
  Spacebot  → working_memory upsert
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from surrealdb import AsyncSurreal

from agent_memory.models import (
    DecisionTrace,
    EdgeKind,
    EvolutionJob,
    EvolutionStatus,
    MemoryCategory,
    MemoryCreate,
    MemoryEdge,
    MemoryQuery,
    MemoryQueryResult,
    MemoryRecord,
    RetrievalTier,
    RetrievalTrace,
    SupersedeRequest,
    WorkingMemory,
    WorkingMemoryLayer,
)

log = logging.getLogger(__name__)


class SurrealMemoryClient:
    """
    Production SurrealDB client for Agent-Memory.

    All writes are ACID-transactional (SurrealDB guarantees this within
    a single query/transaction block).
    """

    def __init__(
        self,
        url: str,
        namespace: str,
        database: str,
        username: str,
        password: str,
    ) -> None:
        self._url = url
        self._ns = namespace
        self._db = database
        self._username = username
        self._password = password
        self.client = AsyncSurreal(url)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        await self.client.connect()
        await self.client.signin({"username": self._username, "password": self._password})
        await self.client.use(self._ns, self._db)
        log.info("SurrealMemoryClient connected to %s / %s / %s", self._url, self._ns, self._db)

    async def close(self) -> None:
        await self.client.close()

    # ------------------------------------------------------------------
    # Memory — create
    # ------------------------------------------------------------------

    async def create_memory(self, payload: MemoryCreate) -> MemoryRecord:
        """
        Create a new memory record.
        SurrealDB DEFINE EVENT fires evolution_queue job automatically.
        """
        data = payload.model_dump(exclude_none=True)
        result = await self.client.create("memory", data)
        return MemoryRecord(**result)

    # ------------------------------------------------------------------
    # Memory — supersede  (Spectron: never overwrite, always supersede)
    # ------------------------------------------------------------------

    async def supersede_memory(self, req: SupersedeRequest) -> tuple[MemoryRecord, MemoryRecord]:
        """
        Supersede an existing memory:
          1. Mark old record as superseded (valid_time_end = now, superseded = true)
          2. Create new record with derived_from pointing to old
          3. Create 'updates' graph edge new → old
        Returns (old_record, new_record).
        """
        now_iso = datetime.utcnow().isoformat() + "Z"

        surql = """
        BEGIN TRANSACTION;

        -- Step 1: mark old as superseded
        UPDATE type::thing('memory', $old_id) SET
            superseded      = true,
            superseded_at   = time::now(),
            valid_time_end  = time::now(),
            updated_at      = time::now();

        -- Step 2: create new memory
        LET $new = (CREATE memory SET
            category        = (SELECT category FROM type::thing('memory', $old_id))[0].category,
            content         = $new_content,
            agent_id        = (SELECT agent_id FROM type::thing('memory', $old_id))[0].agent_id,
            session_id      = (SELECT session_id FROM type::thing('memory', $old_id))[0].session_id,
            scope           = (SELECT scope FROM type::thing('memory', $old_id))[0].scope,
            source_kind     = $source_kind,
            source_ref      = $source_ref,
            confidence      = $confidence,
            source_trust    = (SELECT source_trust FROM type::thing('memory', $old_id))[0].source_trust,
            derived_from    = [type::thing('memory', $old_id)],
            embedding       = $embedding,
            known_time      = time::now(),
            created_at      = time::now(),
            updated_at      = time::now()
        );

        -- Step 3: update old.superseded_by
        UPDATE type::thing('memory', $old_id) SET
            superseded_by = $new.id;

        -- Step 4: graph edge
        RELATE $new->mem_edge->type::thing('memory', $old_id)
            SET kind = 'updates', weight = 1.0, created_at = time::now();

        RETURN $new;
        COMMIT TRANSACTION;
        """

        result = await self.client.query(surql, {
            "old_id":       req.old_memory_id.split(":")[-1],
            "new_content":  req.new_content,
            "source_kind":  req.new_source_kind.value,
            "source_ref":   req.new_source_ref,
            "confidence":   req.new_confidence,
            "embedding":    req.new_embedding,
        })

        old_raw = await self.client.select(req.old_memory_id)
        old = MemoryRecord(**old_raw)
        new = MemoryRecord(**result[-1][0])
        return old, new

    # ------------------------------------------------------------------
    # Memory — retrieve (hybrid)
    # ------------------------------------------------------------------

    async def query_memories(self, q: MemoryQuery) -> MemoryQueryResult:
        """
        Hybrid retrieval: vector (HNSW) + BM25 full-text merged via RRF.
        Traces are written automatically and returned.
        Respects Spectron four-tier ladder via q.tier.
        """
        # Tier 1: direct lookup by category/scope (no embedding needed)
        if q.tier == RetrievalTier.DIRECT_LOOKUP:
            return await self._direct_lookup(q)

        # Tier 2: response reuse — not implemented here (needs response cache table)
        # Fall through to hybrid

        # Tier 3 + 4: hybrid
        return await self._hybrid_retrieve(q)

    async def _direct_lookup(self, q: MemoryQuery) -> MemoryQueryResult:
        filters = ["agent_id = $agent_id", "superseded = false"]
        vars: dict[str, Any] = {"agent_id": q.agent_id, "limit": q.top_k}

        if q.categories:
            filters.append("category IN $categories")
            vars["categories"] = [c.value for c in q.categories]
        if q.scope:
            filters.append("scope = $scope")
            vars["scope"] = q.scope.value
        if q.valid_at:
            filters.append("(valid_time_start IS NONE OR valid_time_start <= $valid_at)")
            filters.append("(valid_time_end IS NONE OR valid_time_end >= $valid_at)")
            vars["valid_at"] = q.valid_at.isoformat()
        if q.min_confidence > 0:
            filters.append("confidence >= $min_confidence")
            vars["min_confidence"] = q.min_confidence

        where = " AND ".join(filters)
        surql = f"SELECT * FROM memory WHERE {where} ORDER BY importance DESC LIMIT $limit;"
        rows = await self.client.query(surql, vars)
        memories = [MemoryRecord(**r) for r in (rows[0] if rows else [])]

        trace = await self._write_trace(q, memories, RetrievalTier.DIRECT_LOOKUP)
        return MemoryQueryResult(
            memories=memories,
            trace_id=trace.id,
            tier_used=RetrievalTier.DIRECT_LOOKUP,
            total_candidates=len(memories),
        )

    async def _hybrid_retrieve(self, q: MemoryQuery) -> MemoryQueryResult:
        """
        Vector search merged with BM25 via Reciprocal Rank Fusion.
        If no embedding provided, falls back to BM25 only.
        """
        vars: dict[str, Any] = {
            "agent_id":       q.agent_id,
            "query":          q.query_text,
            "limit":          q.top_k,
            "min_confidence": q.min_confidence,
        }

        active_filter = "superseded = false" if not q.include_superseded else "true"
        cat_filter = ""
        if q.categories:
            cat_filter = "AND category IN $categories"
            vars["categories"] = [c.value for c in q.categories]

        # BM25 branch
        bm25_surql = f"""
        SELECT id, content, category, confidence, importance,
               search::score(1) AS bm25_score
        FROM memory
        WHERE {active_filter}
            AND agent_id = $agent_id
            AND content @1@ $query
            {cat_filter}
            AND confidence >= $min_confidence
        ORDER BY bm25_score DESC
        LIMIT $limit;
        """

        rows_bm25 = await self.client.query(bm25_surql, vars)
        bm25_results: list[dict] = rows_bm25[0] if rows_bm25 else []

        # Vector branch (only if embedding provided)
        vec_results: list[dict] = []
        if q.query_embedding:
            vars["embedding"] = q.query_embedding
            vec_surql = f"""
            SELECT id, content, category, confidence, importance,
                   vector::similarity::cosine(embedding, $embedding) AS vec_score
            FROM memory
            WHERE {active_filter}
                AND agent_id = $agent_id
                {cat_filter}
                AND confidence >= $min_confidence
                AND embedding IS NOT NONE
            ORDER BY vec_score DESC
            LIMIT $limit;
            """
            rows_vec = await self.client.query(vec_surql, vars)
            vec_results = rows_vec[0] if rows_vec else []

        # RRF merge
        merged_ids = _reciprocal_rank_fusion(
            [r["id"] for r in bm25_results],
            [r["id"] for r in vec_results],
            k=60,
            top_n=q.top_k,
        )

        # Fetch full records for merged IDs
        memories: list[MemoryRecord] = []
        for rid in merged_ids:
            raw = await self.client.select(rid)
            if raw:
                memories.append(MemoryRecord(**raw))

        trace = await self._write_trace(q, memories, q.tier)
        return MemoryQueryResult(
            memories=memories,
            trace_id=trace.id,
            tier_used=q.tier,
            total_candidates=len(bm25_results) + len(vec_results),
        )

    # ------------------------------------------------------------------
    # Retrieval trace
    # ------------------------------------------------------------------

    async def _write_trace(
        self,
        q: MemoryQuery,
        results: list[MemoryRecord],
        tier: RetrievalTier,
    ) -> RetrievalTrace:
        data = {
            "agent_id":        q.agent_id,
            "session_id":      q.session_id,
            "query_text":      q.query_text,
            "query_embedding": q.query_embedding,
            "tier":            tier.value,
            "result_ids":      [m.id for m in results if m.id],
            "created_at":      datetime.utcnow().isoformat() + "Z",
        }
        raw = await self.client.create("retrieval_trace", data)
        return RetrievalTrace(**raw)

    async def feedback_trace(
        self,
        trace_id: str,
        useful: bool | None = None,
        correction: bool | None = None,
    ) -> None:
        """Record feedback on a retrieval trace (boosts/demotes future ranking)."""
        updates: dict[str, Any] = {}
        if useful is not None:
            updates["useful"] = useful
        if correction is not None:
            updates["correction"] = correction
        if updates:
            await self.client.merge(trace_id, updates)

    # ------------------------------------------------------------------
    # Graph edges
    # ------------------------------------------------------------------

    async def relate_memories(
        self,
        source_id: str,
        target_id: str,
        kind: EdgeKind,
        weight: float = 1.0,
    ) -> MemoryEdge:
        surql = """
        RELATE type::thing('memory', $src)->mem_edge->type::thing('memory', $tgt)
            SET kind = $kind, weight = $weight, created_at = time::now();
        """
        raw = await self.client.query(surql, {
            "src":    source_id.split(":")[-1],
            "tgt":    target_id.split(":")[-1],
            "kind":   kind.value,
            "weight": weight,
        })
        r = raw[0][0]
        return MemoryEdge(
            id=str(r.get("id")),
            source_id=source_id,
            target_id=target_id,
            kind=kind,
            weight=weight,
        )

    async def get_related_memories(
        self,
        memory_id: str,
        kinds: list[EdgeKind] | None = None,
        depth: int = 1,
    ) -> list[MemoryRecord]:
        """Graph traversal from a seed memory."""
        kind_filter = ""
        vars: dict[str, Any] = {
            "mem_id": memory_id,
            "depth":  depth,
        }
        if kinds:
            kind_filter = "WHERE kind IN $kinds"
            vars["kinds"] = [k.value for k in kinds]

        surql = f"""
        SELECT ->mem_edge{kind_filter}->memory.* AS related
        FROM type::thing('memory', string::split($mem_id, ':')[1]);
        """
        rows = await self.client.query(surql, vars)
        related = rows[0][0].get("related", []) if rows and rows[0] else []
        return [MemoryRecord(**r) for r in related]

    # ------------------------------------------------------------------
    # Decision trace
    # ------------------------------------------------------------------

    async def create_decision_trace(self, trace: DecisionTrace) -> DecisionTrace:
        data = trace.model_dump(exclude_none=True, exclude={"id"})
        raw = await self.client.create("decision_trace", data)
        return DecisionTrace(**raw)

    # ------------------------------------------------------------------
    # Working memory  (Spacebot Cortex)
    # ------------------------------------------------------------------

    async def upsert_working_memory(self, wm: WorkingMemory) -> WorkingMemory:
        """
        Upsert a working memory layer for an agent.
        One row per (agent_id, layer) — enforced by UNIQUE index.
        """
        surql = """
        UPSERT working_memory
            (agent_id, layer)
            VALUES ($agent_id, $layer)
            ON DUPLICATE KEY UPDATE
                content          = $content,
                source_memories  = $source_memories,
                valid_date       = $valid_date,
                token_count      = $token_count,
                updated_at       = time::now();
        """
        # SurrealDB doesn't have MySQL-style UPSERT; use MERGE on a deterministic ID
        wm_id = f"working_memory:{wm.agent_id}_{wm.layer.value}"
        data = {
            "agent_id":        wm.agent_id,
            "layer":           wm.layer.value,
            "content":         wm.content,
            "source_memories": wm.source_memories,
            "valid_date":      wm.valid_date.isoformat() if wm.valid_date else None,
            "token_count":     wm.token_count,
            "updated_at":      datetime.utcnow().isoformat() + "Z",
        }
        try:
            raw = await self.client.merge(wm_id, data)
        except Exception:
            # Record doesn't exist yet — create it
            data["created_at"] = datetime.utcnow().isoformat() + "Z"
            raw = await self.client.create("working_memory", data)
        return WorkingMemory(**raw)

    async def get_working_memory(
        self,
        agent_id: str,
        layers: list[WorkingMemoryLayer] | None = None,
    ) -> list[WorkingMemory]:
        """Fetch assembled Cortex context for an agent."""
        vars: dict[str, Any] = {"agent_id": agent_id}
        layer_filter = ""
        if layers:
            layer_filter = "AND layer IN $layers"
            vars["layers"] = [l.value for l in layers]

        surql = f"""
        SELECT * FROM working_memory
        WHERE agent_id = $agent_id {layer_filter}
        ORDER BY layer;
        """
        rows = await self.client.query(surql, vars)
        return [WorkingMemory(**r) for r in (rows[0] if rows else [])]

    # ------------------------------------------------------------------
    # Evolution queue  (A-Mem)
    # ------------------------------------------------------------------

    async def pop_evolution_jobs(
        self,
        agent_id: str,
        limit: int = 20,
    ) -> list[EvolutionJob]:
        """Claim pending evolution jobs for processing."""
        surql = """
        UPDATE evolution_queue
        SET status = 'processing'
        WHERE agent_id = $agent_id AND status = 'pending'
        LIMIT $limit
        RETURN AFTER;
        """
        rows = await self.client.query(surql, {"agent_id": agent_id, "limit": limit})
        return [EvolutionJob(**r) for r in (rows[0] if rows else [])]

    async def complete_evolution_job(self, job_id: str) -> None:
        await self.client.merge(job_id, {
            "status":       EvolutionStatus.DONE.value,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        })

    async def skip_evolution_job(self, job_id: str) -> None:
        await self.client.merge(job_id, {
            "status":       EvolutionStatus.SKIPPED.value,
            "processed_at": datetime.utcnow().isoformat() + "Z",
        })

    # ------------------------------------------------------------------
    # Temporal queries  (Spectron tri-temporal)
    # ------------------------------------------------------------------

    async def memories_valid_at(
        self,
        agent_id: str,
        point_in_time: datetime,
        categories: list[MemoryCategory] | None = None,
    ) -> list[MemoryRecord]:
        """
        Return memories whose valid_time window covers a point in time.
        Answers: "what did the agent believe to be true at T?"
        """
        cat_filter = ""
        vars: dict[str, Any] = {
            "agent_id": agent_id,
            "pit":      point_in_time.isoformat(),
        }
        if categories:
            cat_filter = "AND category IN $categories"
            vars["categories"] = [c.value for c in categories]

        surql = f"""
        SELECT * FROM memory
        WHERE agent_id = $agent_id
            AND (valid_time_start IS NONE OR valid_time_start <= type::datetime($pit))
            AND (valid_time_end   IS NONE OR valid_time_end   >= type::datetime($pit))
            {cat_filter}
        ORDER BY confidence DESC;
        """
        rows = await self.client.query(surql, vars)
        return [MemoryRecord(**r) for r in (rows[0] if rows else [])]

    async def supersession_lineage(self, memory_id: str) -> list[MemoryRecord]:
        """
        Walk the supersession chain for a memory (Spectron: history is queryable).
        Returns chain from newest to oldest.
        """
        surql = """
        SELECT * FROM memory
        WHERE id = $id OR superseded_by = $id OR derived_from CONTAINS $id
        ORDER BY created_at DESC;
        """
        rows = await self.client.query(surql, {"id": memory_id})
        return [MemoryRecord(**r) for r in (rows[0] if rows else [])]

    # ------------------------------------------------------------------
    # Raw query escape hatch
    # ------------------------------------------------------------------

    async def query(self, sql: str, variables: dict[str, Any] | None = None) -> Any:
        return await self.client.query(sql, variables or {})

    async def select(self, record_id: str) -> dict | None:
        return await self.client.select(record_id)


# ---------------------------------------------------------------------------
# RRF helper
# ---------------------------------------------------------------------------

def _reciprocal_rank_fusion(
    list_a: list[str],
    list_b: list[str],
    k: int = 60,
    top_n: int = 10,
) -> list[str]:
    """Merge two ranked lists via Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    for rank, doc_id in enumerate(list_a, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    for rank, doc_id in enumerate(list_b, start=1):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores, key=lambda x: scores[x], reverse=True)[:top_n]
