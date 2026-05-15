#!/usr/bin/env python3
"""
Sample Agent: Voice AI Agent

Based on PolyAI case study + blog
- Voice AI with RAG
- Low latency knowledge base
- Multimodal context
"""

import asyncio
from surrealdb import Surreal


class VoiceAgent:
    """Voice AI agent with memory."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "voice", "database": "ai"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Voice agent schema."""
        schemas = [
            """
            DEFINE TABLE caller SCHEMAFULL;
            DEFINE FIELD name ON caller TYPE string;
            DEFINE FIELD phone ON caller TYPE string;
            DEFINE FIELD history ON caller TYPE array<string>;
            DEFINE FIELD preferences ON caller TYPE object;
            """,
            """
            DEFINE TABLE conversation SCHEMAFULL;
            DEFINE FIELD caller ON conversation TYPE record(caller);
            DEFINE FIELD transcript ON conversation TYPE string;
            DEFINE FIELD intent ON conversation TYPE string;
            DEFINE FIELD entities ON conversation TYPE object;
            DEFINE FIELD resolved ON conversation TYPE bool;
            """,
            """
            DEFINE TABLE knowledge_base SCHEMAFULL;
            DEFINE FIELD question ON knowledge_base TYPE string;
            DEFINE FIELD answer ON knowledge_base TYPE string;
            DEFINE FIELD embedding ON knowledge_base TYPE array<float>;
            DEFINE FIELD category ON knowledge_base TYPE string;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Voice agent schema created")
    
    # ----- Caller Management -----
    
    async def register_caller(self, name: str, phone: str, 
                         preferences: dict = None) -> dict:
        """Register caller."""
        result = await self.db.query(
            "CREATE caller SET name=$name, phone=$phone, preferences=$pref, history=[]",
            {"name": name, "phone": phone, "pref": preferences or {}}
        )
        return result[0][0]
    
    # ----- Conversation -----
    
    async def start_conversation(self, caller_id: str) -> dict:
        """Start new conversation."""
        result = await self.db.query(
            """CREATE conversation SET caller=$caller, transcript='', intent='',
            entities={}, resolved=false""",
            {"caller": caller_id}
        )
        return result[0][0]
    
    async def transcribe(self, conversation_id: str, audio_transcript: str) -> dict:
        """Process audio transcript."""
        result = await self.db.query(
            "UPDATE conversation SET transcript=$transcript WHERE id = $id",
            {"id": conversation_id, "transcript": audio_transcript}
        )
        return result[0][0]
    
    # ----- Intent & Entities -----
    
    async def extract_intent(self, transcript: str) -> dict:
        """Extract intent from transcript."""
        # Simple keyword matching (would use LLM in production)
        intent = "general"
        entities = {}
        
        if any(w in transcript.lower() for w in ["refund", "money back"]):
            intent = "refund"
        elif any(w in transcript.lower() for w in ["cancel", "end"]):
            intent = "cancel"
        elif any(w in transcript.lower() for w in ["help", "support"]):
            intent = "support"
        
        return {"intent": intent, "entities": entities}
    
    # ----- Knowledge Base -----
    
    async def add_knowledge(self, question: str, answer: str, 
                       category: str = "general") -> dict:
        """Add to knowledge base."""
        result = await self.db.query(
            """CREATE knowledge_base SET question=$q, answer=$a, category=$cat""",
            {"q": question, "a": answer, "cat": category}
        )
        return result[0][0]
    
    async def search_knowledge(self, query: str, k: int = 3) -> dict:
        """Search knowledge base."""
        query_emb = [0.1] * 384  # Placeholder
        
        result = await self.db.query(
            f"""SELECT *, vector::distance::knn() AS score FROM knowledge_base 
            WHERE embedding <|{k}|> $query
            ORDER BY score ASC""",
            {"query": query_emb, "k": k}
        )
        
        if result and result[0]:
            return {"answer": result[0][0].get("answer"), "score": result[0][0].get("score")}
        
        return {"answer": "I couldn't find that information."}
    
    # ----- Response Generation -----
    
    async def generate_response(self, conversation_id: str) -> dict:
        """Generate voice response."""
        conv = await self.db.query(
            "SELECT * FROM conversation WHERE id = $id",
            {"id": conversation_id}
        )
        
        if not conv or not conv[0]:
            return {"response": "Hello, how can I help?"}
        
        transcript = conv[0][0].get("transcript", "")
        
        # Extract intent
        intent_data = await self.extract_intent(transcript)
        
        # Search knowledge
        kb = await self.search_knowledge(transcript)
        
        return {
            "intent": intent_data["intent"],
            "response": kb["answer"],
            "resolved": False
        }


async def demo():
    """Demo."""
    agent = VoiceAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Register caller
    caller = await agent.register_caller("John", "+1234567890")
    print(f"Caller: {caller['id']}")


if __name__ == "__main__":
    asyncio.run(demo())