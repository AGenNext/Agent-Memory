#!/usr/bin/env python3
"""
Tool: Knowledge Graph with Ontological Modeling

Rich edges, vector search, graph traversal.
Reference: SurrealDB Knowledge Graphs
"""

import asyncio
from surrealdb import Surreal


class KnowledgeGraphTool:
    """Knowledge graph tool."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "knowledge", "database": "graph"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- Define Ontology -----
    
    async def define_entity(self, name: str, fields: dict):
        """Define entity with fields."""
        # Build field definitions
        field_defs = []
        for field, ftype in fields.items():
            field_defs.append(f"DEFINE FIELD {field} ON {name} TYPE {ftype};")
        
        await self.db.query(f"DEFINE TABLE {name} SCHEMAFULL;")
        
        for fd in field_defs:
            await self.db.query(fd)
        
        return {"entity": name}
    
    async def define_relation(self, name: str, from_entity: str, to_entity: str,
                         fields: dict = None):
        """Define typed relation."""
        await self.db.query(f"""
            DEFINE TABLE {name} TYPE RELATION FROM {from_entity} TO {to_entity};
        """)
        
        if fields:
            for field, ftype in fields.items():
                await self.db.query(f"""
                    DEFINE FIELD {field} ON {name} TYPE {ftype};
                """)
        
        return {"relation": name}
    
    # ----- Create Nodes -----
    
    async def create_node(self, entity: str, data: dict) -> dict:
        """Create entity node."""
        result = await self.db.query(f"CREATE {entity} SET $data", {"data": data})
        return result[0][0] if result else None
    
    async def create_nodes_bulk(self, entity: str, nodes: list) -> list:
        """Create multiple nodes."""
        results = []
        for node in nodes:
            result = await self.create_node(entity, node)
            results.append(result)
        return results
    
    # ----- Rich Edges -----
    
    async def relate(self, from_id: str, to_id: str, relation: str,
                    properties: dict = None) -> dict:
        """Create relationship with rich metadata."""
        data = properties or {}
        result = await self.db.query(f"""
            RELATE {from_id} -> {relation} -> {to_id} SET $props
        """, {"props": data})
        
        return result[0][0] if result else None
    
    async def update_edge(self, from_id: str, to_id: str, relation: str,
                        properties: dict) -> dict:
        """Update relationship properties."""
        result = await self.db.query(f"""
            UPDATE {from_id}->{relation}->{to_id} SET $props
        """, {"props": properties})
        
        return result[0][0] if result else None
    
    # ----- Graph Traversal -----
    
    async def traverse_outgoing(self, node_id: str, relation: str) -> list:
        """Get outgoing relations."""
        result = await self.db.query(f"""
            SELECT * FROM {node_id}->{relation}->entity
        """)
        return result[0] if result else []
    
    async def traverse_incoming(self, node_id: str, relation: str) -> list:
        """Get incoming relations."""
        result = await self.db.query(f"""
            SELECT * FROM entity<-{relation}<-{node_id}
        """)
        return result[0] if result else []
    
    async def traverse_path(self, from_id: str, to_id: str, 
                           max_hops: int = 3) -> list:
        """Find path between nodes."""
        paths = []
        
        # Try each depth
        for hop in range(1, max_hops + 1):
            query = f"SELECT * FROM {from_id}"
            for i in range(hop):
                query += "->->entity"
            
            result = await self.db.query(query)
            
            if result and result[0]:
                for path in result[0]:
                    if path.get("id", "").endswith(to_id):
                        paths.append(path)
        
        return paths
    
    # ----- Graph + Vector -----
    
    async def create_with_embedding(self, entity: str, data: dict, 
                                  embed_field: str = "embedding",
                                  text: str = None):
        """Create node with embedding."""
        # Get embedding (would use actual embeddings in production)
        embedding = [0.1] * 384  # Placeholder
        
        data[embed_field] = embedding
        data["_text"] = text
        
        return await self.create_node(entity, data)
    
    async def hybrid_search(self, entity: str, text_query: str, vector: list,
                        relation: str = None, filters: dict = None,
                        k: int = 5) -> list:
        """Vector + graph + structural search."""
        # Vector search
        vec_result = await self.db.query(f"""
            SELECT *, vector::distance::knn() AS distance
            FROM {entity}
            WHERE embedding <|{k}|> $vector
        """, {"vector": vector})
        
        # Graph search (if relation specified)
        if relation:
            graph_result = await self.db.query(f"""
                SELECT * FROM {entity}->{relation}->entity
            """)
        
        # Combine
        return vec_result[0] if vec_result else []
    
    # ----- Edge Properties Filter -----
    
    async def filter_edges(self, from_id: str, relation: str, 
                     condition: str) -> list:
        """Filter edges by properties."""
        result = await self.db.query(f"""
            SELECT * FROM {from_id}->{relation}[WHERE {condition}]->entity
        """)
        
        return result[0] if result else []
    
    async def trusted_contacts(self, node_id: str, relation: str = "knows",
                          min_confidence: float = 0.9) -> list:
        """Get trusted contacts (filter on edge confidence)."""
        result = await self.db.query(f"""
            SELECT ->{relation}[WHERE confidence > $min]->person.name AS contacts
            FROM {node_id}
        """, {"min": min_confidence})
        
        return result[0] if result else []


async def demo():
    """Demo knowledge graph."""
    kg = KnowledgeGraphTool()
    await kg.connect()
    
    # Define ontology
    await kg.define_entity("person", {"name": "string", "role": "string"})
    await kg.define_relation("knows", "person", "person", {
        "since": "datetime", "confidence": "float", "context": "string"
    })
    
    # Create nodes
    await kg.create_node("person", {"name": "Alice", "role": "engineer"})
    await kg.create_node("person", {"name": "Bob", "role": "designer"})
    
    # Create rich edge
    await kg.relate("person:alice", "person:bob", "knows", {
        "since": "2024-01-15", "confidence": 0.95, 
        "context": "worked together"
    })
    
    # Traverse
    contacts = await kg.trusted_contacts("person:alice", "knows", 0.9)
    print(f"Trusted: {contacts}")


if __name__ == "__main__":
    asyncio.run(demo())