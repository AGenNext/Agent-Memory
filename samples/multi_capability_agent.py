#!/usr/bin/env python3
"""
Sample Agent: Multi-Capability AI Agent

Based on SurrealDB capabilities:
- LIVE queries (real-time)
- Vector search (HNSW, KNN)
- Knowledge graphs (RELATE)
- Events & triggers
- Functions

This is a full-featured agent that demonstrates multiple SurrealDB capabilities.
"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from surrealdb import Surreal


@dataclass
class Document:
    """Document with embedding."""
    id: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]


@dataclass
class Entity:
    """Knowledge graph entity."""
    id: str
    name: str
    entity_type: str
    properties: Dict[str, Any]


class MultiCapabilityAgent:
    """
    Multi-capability AI agent demonstrating SurrealDB features.
    
    Features:
    - Semantic search (vector similarity)
    - Knowledge graphs (entities + relations)
    - LIVE queries (real-time subscriptions)
    - Events (audit logs)
    - Full-text search (BM25)
    - Time-series (telemetry)
    """
    
    def __init__(self, url: str = "ws://localhost:8000/rpc",
                 namespace: str = "agent", 
                 database: str = "demo"):
        self.url = url
        self.namespace = namespace
        self.database = database
        self.db = None
    
    async def connect(self) -> "MultiCapabilityAgent":
        """Connect to SurrealDB."""
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": self.namespace, "database": self.database})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- Schema Setup -----
    
    async def setup_schema(self):
        """Set up complete schema for all capabilities."""
        print("🔧 Setting up schema...")
        
        # 1. Document store with vectors
        await self.db.query("""
            DEFINE TABLE doc SCHEMAFULL;
            DEFINE FIELD content ON doc TYPE string;
            DEFINE FIELD embedding ON doc TYPE array<float>;
            DEFINE FIELD tags ON doc TYPE array<string>;
            DEFINE FIELD created ON doc TYPE datetime DEFAULT time::now();
        """)
        
        # 2. Knowledge graph entities
        await self.db.query("""
            DEFINE TABLE entity SCHEMAFULL;
            DEFINE FIELD name ON entity TYPE string;
            DEFINE FIELD type ON entity TYPE string;
            DEFINE FIELD properties ON entity TYPE object;
        """)
        
        # 3. Relations
        await self.db.query("""
            DEFINE TABLE related TYPE RELATION FROM entity TO entity;
            DEFINE FIELD type ON related TYPE string;
            DEFINE FIELD strength ON related TYPE float DEFAULT 1.0;
        """)
        
        # 4. Time-series (telemetry)
        await self.db.query("""
            DEFINE TABLE telemetry SCHEMAFULL;
            DEFINE FIELD metric ON telemetry TYPE string;
            DEFINE FIELD value ON telemetry TYPE float;
            DEFINE FIELD timestamp ON telemetry TYPE datetime DEFAULT time::now();
        """)
        
        # 5. Audit log
        await self.db.query("""
            DEFINE TABLE audit_log SCHEMAFULL;
            DEFINE FIELD action ON audit_log TYPE string;
            DEFINE FIELD entity ON audit_log TYPE string;
            DEFINE FIELD data ON audit_log TYPE object;
            DEFINE FIELD timestamp ON audit_log TYPE datetime DEFAULT time::now();
        """)
        
        # Indexes
        await self.db.query("""
            DEFINE INDEX doc_vec ON doc FIELDS embedding HNSW DIMENSION 384 DISTANCE COSINE;
        """)
        
        await self.db.query("""
            DEFINE ANALYZER my_analyzer TOKENIZER basic FILTERS lowercase, ascii;
        """)
        
        await self.db.query("""
            DEFINE INDEX doc_text ON doc FIELDS content SEARCH ANALYZER my_analyzer BM25;
        """)
        
        # Event for audit
        await self.db.query("""
            DEFINE EVENT ON doc WHEN CREATE THEN
                CREATE audit_log SET action = 'create', entity = 'doc', data = this;
        """)
        
        print("✅ Schema ready!")
    
    # ----- Document Operations -----
    
    async def add_document(self, content: str, tags: List[str] = None,
                        embedding: List[float] = None) -> Dict:
        """Add a document with embedding."""
        # Generate embedding (use actual model in production)
        if embedding is None:
            embedding = self._generate_embedding(content)
        
        result = await self.db.query(
            "CREATE doc SET content=$content, tags=$tags, embedding=$emb",
            {"content": content, "tags": tags or [], "emb": embedding}
        )
        
        print(f"📄 Added document: {content[:50]}...")
        return result[0][0]
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate a simple embedding (placeholder)."""
        # In production, use OpenAI, Ollama, etc.
        import hashlib
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        # Generate pseudo-random but deterministic embedding
        return [(hash_val >> i) % 2 for i in range(384)]
    
    async def add_documents_bulk(self, documents: List[Dict]) -> List[Dict]:
        """Add multiple documents."""
        results = []
        for doc in documents:
            result = await self.add_document(
                doc["content"], 
                doc.get("tags"),
                doc.get("embedding")
            )
            results.append(result)
        return results
    
    # ----- Vector Search -----
    
    async def semantic_search(self, query: str, k: int = 5) -> List[Dict]:
        """Search by semantic similarity."""
        query_emb = self._generate_embedding(query)
        
        result = await self.db.query(
            f"""SELECT content, vector::distance::knn() AS distance 
            FROM doc WHERE embedding <|{k}|> $emb 
            ORDER BY distance ASC""",
            {"emb": query_emb, "k": k}
        )
        
        return result[0] if result else []
    
    # ----- Full-Text Search -----
    
    async def fulltext_search(self, query: str, k: int = 5) -> List[Dict]:
        """Search by full text (BM25)."""
        result = await self.db.query(
            f"""SELECT *, search::score() AS score 
            FROM doc WHERE content @@ $query 
            ORDER BY score DESC LIMIT {k}""",
            {"query": query}
        )
        
        return result[0] if result else []
    
    # ----- Hybrid Search -----
    
    async def hybrid_search(self, query: str, k: int = 5) -> Dict:
        """Combine vector + full-text search."""
        semantic = await self.semantic_search(query, k)
        fulltext = await self.fulltext_search(query, k)
        
        # RRF fusion
        if semantic and fulltext:
            rrf_result = await self.db.query("""
                SELECT * FROM search::rrf([$vec, $text], 5, 20)
            """, {"vec": semantic, "text": fulltext})
            return {"results": rrf_result[0] if rrf_result else [], "combined": True}
        
        return {"results": semantic or fulltext, "combined": False}
    
    # ----- Knowledge Graph -----
    
    async def create_entity(self, name: str, entity_type: str, 
                       properties: Dict = None) -> Dict:
        """Create knowledge graph entity."""
        result = await self.db.query(
            "CREATE entity SET name=$name, type=$type, properties=$props",
            {"name": name, "type": entity_type, "props": properties or {}}
        )
        
        print(f"🏷️ Created entity: {name} ({entity_type})")
        return result[0][0]
    
    async def relate_entities(self, from_entity: str, to_entity: str,
                           relation_type: str, strength: float = 1.0) -> Dict:
        """Create relation between entities."""
        result = await self.db.query(
            """RELATE entity:$from -> related -> entity:$to 
            SET type=$rel, strength=$strength""",
            {"from": from_entity, "to": to_entity, "rel": relation_type, 
             "strength": strength}
        )
        
        print(f"🔗 Related: {from_entity} --[{relation_type}]--> {to_entity}")
        return result[0][0]
    
    async def get_entity_relations(self, entity: str) -> List[Dict]:
        """Get all relations for an entity."""
        result = await self.db.query(
            """SELECT <-related->entity AS connected, related.type AS rel_type
            FROM entity:$e""",
            {"e": entity}
        )
        
        return result[0] if result else []
    
    async def traverse_graph(self, start_entity: str, max_depth: int = 2) -> List[Dict]:
        """Traverse knowledge graph."""
        results = []
        
        for depth in range(max_depth):
            result = await self.get_entity_relations(start_entity)
            if result:
                results.extend(result)
                # Get last entity for next iteration
                if result:
                    start_entity = result[-1].get("connected", {}).get("name", "")
        
        return results
    
    # ----- Time-Series -----
    
    async def record_telemetry(self, metric: str, value: float) -> Dict:
        """Record telemetry data point."""
        result = await self.db.query(
            "CREATE telemetry SET metric=$metric, value=$value",
            {"metric": metric, "value": value}
        )
        
        return result[0][0]
    
    async def get_telemetry(self, metric: str, limit: int = 100) -> List[Dict]:
        """Get telemetry history."""
        result = await self.db.query(
            f"""SELECT * FROM telemetry WHERE metric = $metric 
            ORDER BY timestamp DESC LIMIT {limit}""",
            {"metric": metric}
        )
        
        return result[0] if result else []
    
    async def get_latest_metrics(self) -> Dict:
        """Get latest value for all metrics."""
        result = await self.db.query(
            """SELECT metric, value, timestamp FROM telemetry 
            GROUP BY metric"""
        )
        
        if result and result[0]:
            return {r.get("metric"): r.get("value") for r in result[0]}
        return {}
    
    # ----- Audit -----
    
    async def get_audit_log(self, limit: int = 50) -> List[Dict]:
        """Get audit log."""
        result = await self.db.query(
            f"""SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT {limit}"""
        )
        
        return result[0] if result else []
    
    # ----- LIVE Queries (Real-time) -----
    
    async def subscribe_to_docs(self, callback) -> None:
        """Subscribe to document changes."""
        # In production, use async for change in self.db.live(...):
        print("📡 Subscribed to doc changes")
    
    # ----- Complete Demo -----
    
    async def run_demo(self):
        """Run complete demonstration."""
        print("\n" + "="*60)
        print("🎯 Multi-Capability Agent Demo")
        print("="*60 + "\n")
        
        # 1. Add documents
        print("📄 Adding documents...")
        await self.add_documents_bulk([
            {"content": "AI agents use memory to maintain context across conversations", 
             "tags": ["ai", "agents", "memory"]},
            {"content": "Vector databases enable semantic search over documents",
             "tags": ["vector", "database", "search"]},
            {"content": "Knowledge graphs represent entities and their relationships",
             "tags": ["graph", "knowledge", "entities"]},
            {"content": "SurrealDB supports real-time subscriptions via LIVE queries",
             "tags": ["realtime", "live", "queries"]},
            {"content": "RAG combines retrieval with generative AI for better answers",
             "tags": ["rag", "ai", "llm"]},
        ])
        
        # 2. Search
        print("\n🔍 Semantic search: 'memory for AI'")
        results = await self.semantic_search("memory for AI", k=3)
        for r in results:
            print(f"   - {r.get('content', '')[:60]}...")
        
        # 3. Full-text search
        print("\n📝 Full-text search: 'search'")
        results = await self.fulltext_search("search", k=3)
        for r in results:
            print(f"   - {r.get('content', '')[:60]}...")
        
        # 4. Hybrid search
        print("\n🔎 Hybrid search: 'search'")
        results = await self.hybrid_search("search", k=3)
        print(f"   Combined {len(results.get('results', []))} results")
        
        # 5. Knowledge graph
        print("\n🏗️ Building knowledge graph...")
        await self.create_entity("SurrealDB", "database", {"type": "multi-model"})
        await self.create_entity("AI Agents", "application", {"type": "ai"})
        await self.create_entity("Vector Search", "feature", {"type": "search"})
        
        await self.relate_entities("SurrealDB", "Vector Search", "has_feature")
        await self.relate_entities("SurrealDB", "AI Agents", "powers")
        
        relations = await self.get_entity_relations("SurrealDB")
        print(f"   SurrealDB has {len(relations)} connections")
        
        # 6. Telemetry
        print("\n📊 Recording telemetry...")
        await self.record_telemetry("requests", 100)
        await self.record_telemetry("latency", 45.5)
        
        metrics = await self.get_latest_metrics()
        print(f"   Current metrics: {metrics}")
        
        # 7. Audit log
        print("\n📋 Audit log:")
        logs = await self.get_audit_log()
        print(f"   {len(logs)} entries")
        
        print("\n" + "="*60)
        print("✅ Demo complete!")
        print("="*60)


async def main():
    """Run the demo."""
    agent = MultiCapabilityAgent()
    await agent.connect()
    await agent.setup_schema()
    await agent.run_demo()


if __name__ == "__main__":
    asyncio.run(main())