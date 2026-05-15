#!/usr/bin/env python3
"""
Sample Agent: Knowledge Lake

Based on: "The new era of data lakes, knowledge lakes"
- Unified storage
- Knowledge graphs + vectors
- Semantic search
"""

import asyncio
from surrealdb import Surreal


class KnowledgeLakeAgent:
    """Knowledge lake agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "knowledge_lake", "database": "unified"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Knowledge lake schema."""
        schemas = [
            """
            DEFINE TABLE data_source SCHEMAFULL;
            DEFINE FIELD name ON data_source TYPE string;
            DEFINE FIELD type ON data_source TYPE string; -- doc, table, stream, api
            DEFINE FIELD url ON data_source TYPE string;
            DEFINE FIELD schema ON data_source TYPE object;
            DEFINE FIELD synced_at ON data_source TYPE datetime;
            """,
            """
            DEFINE TABLE record SCHEMAFULL;
            DEFINE FIELD source ON record TYPE record(data_source);
            DEFINE FIELD external_id ON record TYPE string;
            DEFINE FIELD data ON record TYPE object;
            DEFINE FIELD content ON record TYPE string;
            DEFINE FIELD embedding ON record TYPE array<float>;
            """,
            """
            DEFINE TABLE entity SCHEMAFULL;
            DEFINE FIELD name ON entity TYPE string;
            DEFINE FIELD type ON entity TYPE string;
            DEFINE FIELD properties ON entity TYPE object;
            """,
            """
            DEFINE TABLE relates TYPE RELATION FROM entity TO entity;
            """,
        ]
        
        # Create indexes
        await self.db.query("""
            DEFINE INDEX record_vec ON record FIELDS embedding HNSW DIMENSION 1536 DISTANCE COSINE;
        """)
        
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Knowledge lake schema created")
    
    # ----- Data Sources -----
    
    async def register_source(self, name: str, source_type: str, 
                         url: str, schema: dict = None) -> dict:
        """Register data source."""
        result = await self.db.query(
            """CREATE data_source SET name=$name, type=$type, url=$url, 
            schema=$schema, synced_at=time::now()""",
            {"name": name, "type": source_type, "url": url, "schema": schema or {}}
        )
        return result[0][0]
    
    # ----- Ingests -----
    
    async def ingest(self, source_id: str, external_id: str, 
                 data: dict, content: str = None) -> dict:
        """Ingest record."""
        result = await self.db.query(
            """CREATE record SET source=$source, external_id=$eid, 
            data=$data, content=$content""",
            {"source": source_id, "eid": external_id, "data": data, "content": content or ""}
        )
        return result[0][0]
    
    # ----- Knowledge Graph -----
    
    async def create_entity(self, name: str, entity_type: str, 
                       properties: dict = None) -> dict:
        """Create entity."""
        result = await self.db.query(
            "CREATE entity SET name=$name, type=$type, properties=$props",
            {"name": name, "type": entity_type, "props": properties or {}}
        )
        return result[0][0]
    
    async def relate(self, from_entity: str, to_entity: str,
                   relation: str) -> dict:
        """Create relation."""
        result = await self.db.query(
            "RELATE entity:$from -> relates -> entity:$to SET type=$rel",
            {"from": from_entity, "to": to_entity, "rel": relation}
        )
        return result[0][0]
    
    # ----- Semantic Search -----
    
    async def search(self, query: str, k: int = 5) -> list:
        """Search across all data."""
        query_emb = [0.1] * 1536  # Would use actual embeddings
        
        result = await self.db.query(f"""
            SELECT *, vector::distance::knn() AS distance
            FROM record WHERE embedding <|{k}|> $emb
            ORDER BY distance ASC
        """, {"emb": query_emb, "k": k})
        
        return result[0] if result else []
    
    # ----- Graph Traversal -----
    
    async def get_connected_entities(self, entity: str, 
                                  depth: int = 2) -> list:
        """Get connected entities."""
        result = await self.db.query(
            """SELECT ->relates->entity AS connected FROM entity:$e""",
            {"e": entity}
        )
        return result[0] if result else []
    
    # ----- Unified Query -----
    
    async def query(self, question: str) -> dict:
        """Query knowledge lake."""
        # Semantic search
        semantic = await self.search(question)
        
        # Graph relations
        entities = await self.get_connected_entities("topic:AI")
        
        return {
            "question": question,
            "semantic_results": semantic[:3],
            "entities": entities,
            "answer": "Based on knowledge lake..."
        }


async def demo():
    """Demo."""
    agent = KnowledgeLakeAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Register source
    source = await agent.register_source("docs", "doc", "/docs")
    print(f"Source: {source['id']}")


if __name__ == "__main__":
    asyncio.run(demo())