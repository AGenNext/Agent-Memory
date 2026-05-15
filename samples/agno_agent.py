#!/usr/bin/env python3
"""
Sample Agent: Agno Memory Agent

Based on: Agno + SurrealDB integration
- Session storage
- Memory provider
- Knowledge snapshots
- Metrics tracking
"""

import asyncio
from surrealdb import Surreal


class AgnoMemoryAgent:
    """Agno memory agent for SurrealDB."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "agno", "database": "memory"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Agno memory schema."""
        schemas = [
            """
            DEFINE TABLE session SCHEMAFULL;
            DEFINE FIELD agent_id ON session TYPE string;
            DEFINE FIELD user_id ON session TYPE string;
            DEFINE FIELD context ON session TYPE object;
            DEFINE FIELD tokens_used ON session TYPE int;
            DEFINE FIELD duration ON session TYPE int;
            DEFINE FIELD created ON session TYPE datetime;
            """,
            """
            DEFINE TABLE memory SCHEMAFULL;
            DEFINE FIELD session ON memory TYPE record(session);
            DEFINE FIELD type ON memory TYPE string; -- short_term, long_term, working
            DEFINE FIELD content ON memory TYPE string;
            DEFINE FIELD embedding ON memory TYPE array<float>;
            DEFINE FIELD importance ON memory TYPE float DEFAULT 1.0;
            """,
            """
            DEFINE TABLE knowledge SCHEMAFULL;
            DEFINE FIELD title ON knowledge TYPE string;
            DEFINE FIELD content ON knowledge TYPE string;
            DEFINE FIELD embedding ON knowledge TYPE array<float>;
            DEFINE FIELD tags ON knowledge TYPE array<string>;
            DEFINE FIELD created ON knowledge TYPE datetime;
            """,
            """
            DEFINE TABLE eval SCHEMAFULL;
            DEFINE FIELD agent_id ON eval TYPE string;
            DEFINE FIELD input ON eval TYPE string;
            DEFINE FIELD output ON eval TYPE string;
            DEFINE FIELD score ON eval TYPE float;
            DEFINE FIELD metrics ON eval TYPE object;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Agno memory schema created")
    
    # ----- Session -----
    
    async def create_session(self, agent_id: str, user_id: str, 
                         context: dict = None) -> dict:
        """Create session."""
        result = await self.db.query(
            """CREATE session SET agent_id=$agent, user_id=$user, 
            context=$ctx, tokens_used=0, duration=0, created=time::now()""",
            {"agent": agent_id, "user": user_id, "ctx": context or {}}
        )
        return result[0][0]
    
    async def end_session(self, session_id: str, tokens: int, duration: int):
        """End and update session."""
        result = await self.db.query(
            "UPDATE session SET tokens_used=$tokens, duration=$dur WHERE id = $id",
            {"id": session_id, "tokens": tokens, "dur": duration}
        )
        return result[0][0]
    
    # ----- Memory -----
    
    async def store_memory(self, session_id: str, memory_type: str,
                       content: str, importance: float = 1.0) -> dict:
        """Store memory."""
        result = await self.db.query(
            """CREATE memory SET session=$session, type=$type, 
            content=$content, importance=$imp""",
            {"session": session_id, "type": memory_type, 
             "content": content, "imp": importance}
        )
        return result[0][0]
    
    async def retrieve_memory(self, session_id: str, memory_type: str = None,
                        k: int = 5) -> list:
        """Retrieve memory."""
        if memory_type:
            result = await self.db.query(
                f"""SELECT * FROM memory WHERE session = $session AND type = $type 
                ORDER BY importance DESC LIMIT $k""",
                {"session": session_id, "k": k}
            )
        else:
            result = await self.db.query(
                f"""SELECT * FROM memory WHERE session = $session 
                ORDER BY importance DESC LIMIT $k""",
                {"session": session_id, "k": k}
            )
        return result[0] if result else []
    
    # ----- Knowledge -----
    
    async def add_knowledge(self, title: str, content: str, 
                        tags: list = None) -> dict:
        """Add knowledge document."""
        result = await self.db.query(
            """CREATE knowledge SET title=$title, content=$content, 
            tags=$tags, created=time::now()""",
            {"title": title, "content": content, "tags": tags or []}
        )
        return result[0][0]
    
    async def search_knowledge(self, query: str, k: int = 5) -> list:
        """Search knowledge."""
        result = await self.db.query(
            f"""SELECT *, vector::distance::knn() AS score FROM knowledge 
            WHERE embedding <|{k}|> $query
            ORDER BY score ASC""",
            {"query": [0.1] * 384, "k": k}
        )
        return result[0] if result else []
    
    # ----- Eval -----
    
    async def record_eval(self, agent_id: str, input_text: str, output_text: str,
                   score: float, metrics: dict = None) -> dict:
        """Record evaluation."""
        result = await self.db.query(
            """CREATE eval SET agent_id=$agent, input=$input, output=$output, 
            score=$score, metrics=$metrics""",
            {"agent": agent_id, "input": input_text, "output": output_text,
             "score": score, "metrics": metrics or {}}
        )
        return result[0][0]
    
    async def get_agent_metrics(self, agent_id: str) -> dict:
        """Get agent metrics."""
        result = await self.db.query(
            """SELECT count() AS runs, math::mean(score) AS avg_score,
            math::mean(metrics->tokens) AS avg_tokens 
            FROM eval WHERE agent_id = $agent""",
            {"agent": agent_id}
        )
        return result[0][0] if result else {}


async def demo():
    """Demo."""
    agent = AgnoMemoryAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Create session
    session = await agent.create_session("support_agent", "user_123")
    print(f"Session: {session['id']}")
    
    # Store memory
    await agent.store_memory(session["id"], "long_term", 
                        "User prefers email support", 0.9)


if __name__ == "__main__":
    asyncio.run(demo())