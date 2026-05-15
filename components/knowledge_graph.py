#!/usr/bin/env python3
"""
Component: Knowledge Graph

Knowledge graph component for SurrealDB.
Based on: https://surrealdb.com/solutions (Knowledge Graphs use case)
"""

import asyncio
from surrealdb import Surreal


class KnowledgeGraph:
    """Knowledge graph with SurrealDB relations."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "knowledge", "database": "graph"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Knowledge graph schema."""
        schemas = [
            # Entities
            """
            DEFINE TABLE entity SCHEMAFULL;
            DEFINE FIELD name ON entity TYPE string;
            DEFINE FIELD type ON entity TYPE string; -- person, company, concept, document
            DEFINE FIELD description ON entity TYPE string;
            DEFINE FIELD properties ON entity TYPE object;
            DEFINE FIELD embedding ON entity TYPE array<float>;
            """,
            # Relations
            """
            DEFINE TABLE relates TYPE RELATION FROM entity TO entity;
            DEFINE FIELD type ON relates TYPE string; -- knows, works_at, owns, created
            DEFINE FIELD strength ON relates TYPE float DEFAULT 1.0;
            """,
            # Documents
            """
            DEFINE TABLE document SCHEMAFULL;
            DEFINE FIELD title ON document TYPE string;
            DEFINE FIELD content ON document TYPE string;
            DEFINE FIELD url ON document TYPE string;
            DEFINE FIELD embedding ON document TYPE array<float>;
            """,
            # Mentions
            """
            DEFINE TABLE mentions TYPE RELATION FROM document TO entity;
            """,
        ]
        
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Knowledge graph schema created")
    
    # ----- Entity Operations -----
    
    async def add_entity(self, name: str, entity_type: str, description: str = None, 
                     properties: dict = None):
        """Add entity to graph."""
        result = await self.db.query(
            """CREATE entity SET name=$name, type=$type, description=$desc, properties=$props""",
            {"name": name, "type": entity_type, "desc": description, "props": properties or {}}
        )
        return result[0][0]
    
    async def add_entities_bulk(self, entities: list):
        """Add multiple entities."""
        results = []
        for e in entities:
            result = await self.add_entity(e["name"], e["type"], e.get("description"))
            results.append(result)
        return results
    
    # ----- Relation Operations -----
    
    async def relate(self, from_entity: str, to_entity: str, 
                  rel_type: str, strength: float = 1.0):
        """Create relation between entities."""
        result = await self.db.query(
            """RELATE entity:$from -> relates -> entity:$to 
            SET type=$type, strength=$strength""",
            {"from": from_entity, "to": to_entity, "type": rel_type, "strength": strength}
        )
        return result[0][0]
    
    async def relate_bulk(self, relations: list):
        """Add multiple relations."""
        results = []
        for r in relations:
            result = await self.relate(r["from"], r["to"], r["type"], r.get("strength", 1.0))
            results.append(result)
        return results
    
    # ----- Graph Traversal -----
    
    async def get_connected(self, entity: str, rel_type: str = None, depth: int = 1) -> list:
        """Get connected entities."""
        if depth == 1:
            query = "SELECT * FROM entity:$e->relates->entity"
        else:
            query = f"SELECT * FROM entity:$e->relates->entity"
        
        result = await self.db.query(
            "SELECT * FROM entity:$e->relates->entity",
            {"e": entity}
        )
        return result[0] if result else []
    
    async def get_path(self, from_entity: str, to_entity: str) -> list:
        """Find path between entities (simple version)."""
        # Find direct relation
        result = await self.db.query(
            """SELECT ->relates->entity AS connected 
            FROM entity:$from WHERE ->relates->entity.name = $to""",
            {"from": from_entity, "to": to_entity}
        )
        
        if result and result[0] and result[0][0].get("connected"):
            return [{"from": from_entity, "to": to_entity, "type": "direct"}]
        
        # Check 2-hop
        result = await self.db.query(
            """SELECT * FROM entity:$from->relates->entity->relates->entity 
            WHERE name = $to""",
            {"from": from_entity, "to": to_entity}
        )
        
        if result and result[0]:
            return [
                {"from": from_entity, "type": "hop1"},
                {"type": "hop2", "to": to_entity}
            ]
        
        return []
    
    # ----- Search -----
    
    async def search_entities(self, query: str, entity_type: str = None) -> list:
        """Search entities."""
        if entity_type:
            result = await self.db.query(
                """SELECT * FROM entity WHERE name @@ $query AND type = $type""",
                {"query": query, "type": entity_type}
            )
        else:
            result = await self.db.query(
                "SELECT * FROM entity WHERE name @@ $query",
                {"query": query}
            )
        return result[0] if result else []
    
    async def search_relations(self, entity: str, rel_type: str = None) -> list:
        """Search relations for entity."""
        if rel_type:
            result = await self.db.query(
                """SELECT ->relates->entity AS target, relates.type AS rel_type,
                relates.strength AS strength FROM entity:$e 
                WHERE relates.type = $type""",
                {"e": entity, "type": rel_type}
            )
        else:
            result = await self.db.query(
                "SELECT ->relates->entity AS target, relates.type AS rel_type FROM entity:$e",
                {"e": entity}
            )
        return result[0] if result else []


async def demo():
    """Knowledge graph demo."""
    kg = KnowledgeGraph()
    await kg.connect()
    await kg.setup_schema()
    
    # Add entities
    await kg.add_entity("Alice", "person", "AI researcher")
    await kg.add_entity("Bob", "person", "Software engineer")
    await kg.add_entity("SurrealDB", "company", "Database company")
    await kg.add_entity("AI", "concept", "Artificial intelligence")
    
    # Add relations
    await kg.relate("Alice", "SurrealDB", "works_at")
    await kg.relate("Bob", "SurrealDB", "works_at")
    await kg.relate("Alice", "AI", "researches")
    await kg.relate("Bob", "AI", "knows")
    await kg.relate("Alice", "Bob", "knows", 0.8)
    
    # Query
    connected = await kg.get_connected("Alice")
    print(f"Alice knows: {connected}")
    
    path = await kg.get_path("Alice", "SurrealDB")
    print(f"Path: {path}")


if __name__ == "__main__":
    asyncio.run(demo())