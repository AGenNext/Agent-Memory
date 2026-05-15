"""Agent Memory SDK - Client."""

import uuid
from datetime import datetime
from typing import Any, Callable

from pydantic import BaseModel
from surrealdb import Surreal

from .config import Config


class Session(BaseModel):
    """Agent conversation session."""
    id: str
    user_id: str | None = None
    status: str = "active"
    started: datetime | None = None
    ended: datetime | None = None


class Message(BaseModel):
    """Chat message."""
    id: str
    session_id: str
    role: str
    content: str
    created: datetime | None = None


class Entity(BaseModel):
    """Extracted entity from conversation."""
    id: str
    session_id: str
    type: str
    name: str
    properties: dict[str, Any] = {}
    confidence: float = 1.0


class Relationship(BaseModel):
    """Discovered entity relationship."""
    id: str
    session_id: str
    from_entity_id: str
    to_entity_id: str
    relation_type: str
    confidence: float = 1.0


class AgentMemory:
    """
    Agent Memory SDK - Build AI agents with persistent memory.
    
    Example:
        from agent_memory import AgentMemory, Config
        
        config = Config()
        memory = AgentMemory(config)
        
        await memory.connect()
        
        # Create a session
        session = await memory.create_session()
        
        # Add entities
        await memory.add_entity(
            session_id=session.id,
            entity_type="person",
            name="John",
            properties={"email": "john@example.com"}
        )
        
        # Query similar past sessions
        past = await memory.find_similar_sessions(
            query="How do I reset password?",
            limit=3
        )
    """
    
    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self._db: Surreal | None = None
        self._llm: Any = None
        self._session: dict[str, Any] = {}
    
    async def connect(self) -> None:
        """Connect to SurrealDB."""
        self._db = Surreal(self.config.db_url)
        await self._db.signin({
            "username": self.config.db_user,
            "password": self.config.db_pass,
        })
        await self._db.use(self.config.db_namespace, self.config.db_database)
    
    async def close(self) -> None:
        """Close connection."""
        if self._db:
            await self._db.close()
    
    # --- Session ---
    
    async def create_session(self, user_id: str | None = None) -> Session:
        """Create a new conversation session."""
        sid = f"session:{uuid.uuid4().hex[:8]}"
        await self._db.query(
            f"CREATE {sid} SET user_id = $user_id, started = time::now();",
            {"user_id": user_id},
        )
        return Session(id=sid, user_id=user_id, started=datetime.now())
    
    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        result = await self._db.query(
            "SELECT * FROM type::record($id);",
            {"id": session_id},
        )
        rows = self._rows(result)
        if rows:
            r = rows[0]
            return Session(
                id=str(r["id"]),
                user_id=r.get("user_id"),
                status=r.get("status", "active"),
                started=r.get("started"),
                ended=r.get("ended"),
            )
        return None
    
    # --- Entity ---
    
    async def add_entity(
        self,
        session_id: str,
        entity_type: str,
        name: str,
        properties: dict[str, Any] | None = None,
        confidence: float = 1.0,
    ) -> Entity:
        """Add an entity to the session."""
        eid = f"entity:{uuid.uuid4().hex[:8]}"
        await self._db.query(
            f"""CREATE {eid} SET 
                session = $session_id, 
                type = $type, 
                name = $name, 
                properties = $props,
                confidence = $confidence,
                created = time::now();""",
            {
                "session_id": session_id,
                "type": entity_type,
                "name": name,
                "props": properties or {},
                "confidence": confidence,
            },
        )
        return Entity(
            id=eid,
            session_id=session_id,
            type=entity_type,
            name=name,
            properties=properties or {},
            confidence=confidence,
        )
    
    async def get_entities(self, session_id: str) -> list[Entity]:
        """Get all entities for a session."""
        result = await self._db.query(
            "SELECT * FROM entity WHERE session = $session_id;",
            {"session_id": session_id},
        )
        rows = self._rows(result)
        return [
            Entity(
                id=str(r["id"]),
                session_id=r["session"],
                type=r["type"],
                name=r["name"],
                properties=r.get("properties", {}),
                confidence=r.get("confidence", 1.0),
            )
            for r in rows
        ]
    
    # --- Relationship ---
    
    async def add_relationship(
        self,
        session_id: str,
        from_entity_id: str,
        to_entity_id: str,
        relation_type: str,
        confidence: float = 1.0,
    ) -> Relationship:
        """Add a relationship between entities."""
        rid = f"relationship:{uuid.uuid4().hex[:8]}"
        await self._db.query(
            f"""CREATE {rid} SET 
                session = $session_id,
                from_entity = $from_id,
                to_entity = $to_id,
                relation_type = $type,
                confidence = $confidence,
                created = time::now();""",
            {
                "session_id": session_id,
                "from_id": from_entity_id,
                "to_id": to_entity_id,
                "type": relation_type,
                "confidence": confidence,
            },
        )
        return Relationship(
            id=rid,
            session_id=session_id,
            from_entity_id=from_entity_id,
            to_entity_id=to_entity_id,
            relation_type=relation_type,
            confidence=confidence,
        )
    
    # --- Decision Tracing ---
    
    async def trace_decision(
        self,
        session_id: str,
        action: str,
        tool: str | None = None,
        result_summary: str | None = None,
    ) -> str:
        """Trace a decision step."""
        did = f"decision:{uuid.uuid4().hex[:8]}"
        await self._db.query(
            f"""CREATE {did} SET 
                session = $session_id,
                action = $action,
                tool = $tool,
                result_summary = $result,
                created = time::now();""",
            {
                "session_id": session_id,
                "action": action,
                "tool": tool,
                "result": result_summary,
            },
        )
        return did
    
    async def trace_response(
        self,
        session_id: str,
        query: str,
        response: str,
        model: str,
        tokens: int | None = None,
    ) -> str:
        """Trace an LLM response."""
        rid = f"response:{uuid.uuid4().hex[:8]}"
        await self._db.query(
            f"""CREATE {rid} SET 
                session = $session_id,
                query = $query,
                response = $response,
                model = $model,
                token_count = $tokens,
                created = time::now();""",
            {
                "session_id": session_id,
                "query": query,
                "response": response,
                "model": model,
                "tokens": tokens,
            },
        )
        return rid
    
    # --- Semantic Search ---
    
    async def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Semantic search over knowledge base."""
        # Generate embedding (requires LLM client)
        # This is a placeholder - actual implementation would call OpenAI/etc
        raise NotImplementedError("Use add_embeddings() first or provide LLM client")
    
    async def find_similar_sessions(
        self,
        query: str,
        limit: int = 3,
        current_session_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find similar past sessions."""
        # Search response_trace for similar queries
        # Requires embeddings
        result = await self._db.query(
            f"""SELECT query, response, model, created 
                FROM response_trace 
                WHERE session != $current
                ORDER BY created DESC 
                LIMIT $limit;""",
            {"current": current_session_id or "", "limit": limit},
        )
        return self._rows(result)
    
    # --- Graph Traversal ---
    
    async def find_related(
        self,
        record_id: str,
    ) -> dict[str, Any]:
        """Find related entities via graph traversal."""
        table = record_id.split(":")[0]
        
        queries = {
            "entity": """
                SELECT *, 
                    ->has_entity->entity AS related,
                    <-has_entity<-entity AS related_to
                FROM type::record($id);""",
            "article": """
                SELECT *, 
                    ->references->product AS products,
                    ->related_to->article AS related_articles
                FROM type::record($id);""",
            "product": """
                SELECT *,
                    <-references<-article AS articles,
                    <-about<-ticket AS tickets
                FROM type::record($id);""",
        }
        
        query = queries.get(table, "SELECT * FROM type::record($id);")
        result = await self._db.query(query, {"id": record_id})
        rows = self._rows(result)
        return rows[0] if rows else {}
    
    # --- Helpers ---
    
    def _rows(self, result) -> list:
        if not result:
            return []
        first = result[0]
        if isinstance(first, dict):
            return result
        if isinstance(first, list):
            return first
        return []
    
    # --- Context Manager ---
    
    async def __aenter__(self) -> "AgentMemory":
        await self.connect()
        return self
    
    async def __aexit__(self, *args) -> None:
        await self.close()