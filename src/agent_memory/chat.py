"""
Agent Memory Chat Stream - Real-time feature discussion.

This module adds a chat/stream feature where users can discuss
agent memory features in real-time using SurrealDB's live queries.
"""

import asyncio
import uuid

from surrealdb import Surreal
from openai import AsyncOpenAI


class ChatStream:
    """
    Real-time chat stream for discussing agent memory features.
    
    Example:
        stream = ChatStream()
        
        # List the feature discussion channel
        features = await stream.list_channels()
        
        # Stream messages in a channel
        async for msg in stream.stream_messages("features"):
            print(msg)
        
        # Send a message
        await stream.send_message("features", "How does hybrid search work?")
    """
    
    def __init__(self, db: Surreal, llm: AsyncOpenAI | None = None):
        self.db = db
        self.llm = llm
    
    # -- Channel Management --
    
    async def create_channel(
        self,
        name: str,
        description: str | None = None,
        topic: str | None = None,
    ) -> str:
        """Create a new chat channel."""
        cid = f"channel:{uuid.uuid4().hex[:8]}"
        await self.db.query(
            f"""CREATE {cid} SET
                name = $name,
                description = $description,
                topic = $topic,
                created = time::now();""",
            {"name": name, "description": description, "topic": topic},
        )
        return cid
    
    async def list_channels(self, topic: str | None = None) -> list[dict]:
        """List all chat channels, optionally filtered by topic."""
        query = "SELECT * FROM channel"
        params = {}
        
        if topic:
            query += " WHERE topic = $topic"
            params = {"topic": topic}
        
        result = await self.db.query(query, params)
        return self._rows(result)
    
    async def get_channel(self, channel_id: str) -> dict | None:
        """Get a channel by ID."""
        result = await self.db.query(
            "SELECT * FROM type::record($id);",
            {"id": channel_id},
        )
        rows = self._rows(result)
        return rows[0] if rows else None
    
    # -- Messages --
    
    async def send_message(
        self,
        channel_id: str,
        user_id: str,
        content: str,
    ) -> str:
        """Send a message to a channel."""
        mid = f"message:{uuid.uuid4().hex[:8]}"
        await self.db.query(
            f"""CREATE {mid} SET
                channel = $channel_id,
                user = $user_id,
                content = $content,
                created = time::now();""",
            {"channel_id": channel_id, "user": user_id, "content": content},
        )
        return mid
    
    async def get_messages(
        self,
        channel_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """Get messages from a channel."""
        result = await self.db.query(
            f"""SELECT * FROM message 
                WHERE channel = $channel_id 
                ORDER BY created DESC 
                LIMIT $limit;""",
            {"channel_id": channel_id, "limit": limit},
        )
        return self._rows(result)
    
    # -- Live Streaming --
    
    async def stream_messages(self, channel_id: str):
        """Stream new messages in real-time using live queries."""
        # Set up live query
        await self.db.query(
            f"""LIVE SELECT * FROM message 
                WHERE channel = $channel_id 
                ORDER BY created ASC;""",
            {"channel_id": channel_id},
        )
        
        # Listen for changes
        async for msg in self.db.listen():
            yield msg
    
    # -- AI Feature Assistant --
    
    async def ask_about_feature(self, question: str) -> str:
        """
        Ask the AI assistant about agent memory features.
        
        Uses context from the schema and documentation to answer.
        """
        if not self.llm:
            return "LLM not configured"
        
        feature_context = """
        Agent Memory Features in SurrealDB:
        - Knowledge Graph: Entities, relationships stored as graph
        - Entity Extraction: Automatic entity disambiguation
        - Temporal Facts: Bi-temporal history tracking
        - Hybrid Retrieval: Vector + graph + filters in one call
        - Decision Tracing: Audit every agent decision
        - Multi-agent: Shared memory for agent coordination
        
        Schema includes:
        - Tables: session, entity, relationship, decision_step, response_trace
        - Vector indexes: MTREE, HNSW
        - Full-text: BM25 search
        - Extensions: Custom functions in WASM
        - Events: Auto-triggers on table changes
        - CDC: Change data capture
        """
        
        response = await self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert on the Agent Memory schema. Answer questions about its features.\n\n{feature_context}"
                },
                {"role": "user", "content": question}
            ],
        )
        
        return response.choices[0].message.content
    
    async def suggest_features(self, use_case: str) -> list[dict]:
        """
        Suggest relevant features based on a use case.
        
        Example:
            suggestions = await stream.suggest_features("I want to track agent decisions")
        """
        if not self.llm:
            return []
        
        feature_db = [
            {"name": "decision tracing", "tables": ["decision_step", "led_to"], "description": "Track every agent decision"},
            {"name": "semantic search", "tables": ["article", "embedding"], "description": "Vector similarity search"},
            {"name": "hybrid retrieval", "tables": ["article", "product", "ticket"], "description": "Combined vector + graph"},
            {"name": "entity linking", "tables": ["entity", "relationship"], "description": "Connect extracted entities"},
            {"name": "session history", "tables": ["session", "response_trace"], "description": "Past conversations"},
            {"name": "feedback sentiment", "tables": ["feedback", "sentiment"], "description": "User feedback tracking"},
            {"name": "rate limiting", "tables": ["rate_limit", "api_usage"], "description": "API rate controls"},
            {"name": "real-time alerts", "tables": ["alert", "notification"], "description": "Push notifications"},
        ]
        
        response = await self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Given these features and their tables, recommend the most relevant ones for the user's use case. Return a JSON array of {name, tables, description}."
                },
                {"role": "user", "content": use_case}
            ],
        )
        
        # Parse and return suggestions
        import json
        try:
            return json.loads(response.choices[0].message.content)
        except:
            return feature_db[:3]
    
    # -- Channel Topics --
    
    async def get_feature_topics(self) -> list[dict]:
        """Get predefined feature discussion topics."""
        topics = [
            {"id": "knowledge-graph", "name": "Knowledge Graph", "description": "Discuss entity relationships"},
            {"id": "hybrid-search", "name": "Hybrid Search", "description": "Vector + text search"},
            {"id": "decision-tracing", "name": "Decision Tracing", "description": "Agent auditing"},
            {"id": "multi-agent", "name": "Multi-Agent", "description": "Coordination between agents"},
            {"id": "temporal", "name": "Temporal Facts", "description": "Time-based tracking"},
            {"id": "extensions", "name": "Extensions", "description": "WASM functions"},
            {"id": "schema", "name": "Schema Design", "description": "Table design"},
            {"id": "performance", "name": "Performance", "description": "Optimization"},
        ]
        
        # Return as channel list
        return await self.list_channels()
    
    # -- Helpers --
    
    def _rows(self, result) -> list:
        if not result:
            return []
        first = result[0]
        if isinstance(first, dict):
            return result
        if isinstance(first, list):
            return first
        return []


async def demo():
    """Demo the chat stream feature."""
    from agent_memory import AgentMemory, Config
    
    config = Config()
    async with AgentMemory(config) as memory:
        stream = ChatStream(memory._db)
        
        # Show available topics
        print("=== Feature Discussion Topics ===")
        print("Available channels: knowledge-graph, hybrid-search, decision-tracing,")
        print("                        multi-agent, temporal, extensions,")
        print("                        schema, performance")
        
        # Ask about a feature
        print("\n=== Ask About Features ===")
        question = "How does hybrid search work?"
        answer = await stream.ask_about_feature(question)
        print(f"Q: {question}")
        print(f"A: {answer}")
        
        # Get suggestions
        print("\n=== Feature Suggestions ===")
        suggestions = await stream.suggest_features("I want to build a support agent that learns from feedback")
        for s in suggestions[:3]:
            print(f"- {s.get('name', 'N/A')}: {s.get('description', '')}")


if __name__ == "__main__":
    asyncio.run(demo())