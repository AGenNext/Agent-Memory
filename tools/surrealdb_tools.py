#!/usr/bin/env python3
"""
Tool: SurrealDB Agent Tools

Convert sample agents into importable tools.
Usage:
    from tools.surrealdb_tools import (
        vector_search_tool,
        knowledge_graph_tool,
        rag_tool,
        realtime_tool,
    )
    
    # Use as tools
    await vector_search_tool("query", k=5)
    await knowledge_graph_tool("search", "person")
    await rag_tool("question")
    await realtime_tool("subscribe", "messages")
"""

import asyncio
from surrealdb import Surreal
from typing import List, Dict, Any, Optional


class SurrealDBTools:
    """Collection of SurrealDB tools."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "tools", "database": "runtime"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    # ----- Vector Search Tool -----
    
    async def vector_search(self, query: str, table: str = "document", 
                       k: int = 5) -> List[Dict]:
        """Tool: Search by vector similarity."""
        # Generate query embedding
        import hashlib
        hash_val = int(hashlib.md5(query.encode()).hexdigest(), 16)
        emb = [(hash_val >> i) % 2 for i in range(384)]
        
        result = await self.db.query(
            f"""SELECT *, vector::distance::knn() AS score 
            FROM {table} WHERE embedding <|{k}|> $emb 
            ORDER BY score ASC""",
            {"emb": emb, "k": k}
        )
        
        return result[0] if result else []
    
    # ----- Knowledge Graph Tool -----
    
    async def knowledge_graph(self, operation: str, entity: str = None,
                      relation: str = None, to_entity: str = None) -> Dict:
        """Tool: Knowledge graph operations."""
        operation = operation.lower()
        
        if operation == "create":
            result = await self.db.query(
                "CREATE entity SET name=$name, type=$type",
                {"name": entity, "type": relation or "unknown"}
            )
            return {"created": result[0][0] if result else None}
        
        elif operation == "relate":
            result = await self.db.query(
                "RELATE entity:$from -> relates -> entity:$to",
                {"from": entity, "to": to_entity}
            )
            return {"related": True}
        
        elif operation == "search":
            result = await self.db.query(
                "SELECT * FROM entity WHERE name CONTAINS $name",
                {"name": entity}
            )
            return {"results": result[0] if result else []}
        
        return {"error": f"Unknown operation: {operation}"}
    
    # ----- RAG Tool -----
    
    async def rag(self, question: str, k: int = 5) -> Dict:
        """Tool: RAG - retrieve and generate."""
        # Search
        results = await self.vector_search(question, "document", k)
        
        # Build context
        context = "\n\n".join([r.get("content", "") for r in results[:3]])
        
        return {
            "question": question,
            "context": context,
            "sources": [r.get("id") for r in results[:3]],
            "answer": f"Based on {len(results)} sources..."
        }
    
    # ----- Real-Time Tool -----
    
    async def realtime(self, operation: str, table: str = "message",
                    query: str = None) -> Dict:
        """Tool: Real-time operations."""
        operation = operation.lower()
        
        if operation == "subscribe":
            # Would return subscription in production
            return {"subscribed": True, "table": table}
        
        elif operation == "publish":
            await self.db.query(f"CREATE {table} SET content=$content", {"content": query})
            return {"published": True}
        
        elif operation == "watch":
            result = await self.db.query(f"LIVE SELECT * FROM {table}")
            return {"watching": result[0] if result else []}
        
        return {"error": f"Unknown operation: {operation}"}
    
    # ----- Document Tool -----
    
    async def document(self, operation: str, content: str = None,
                   doc_id: str = None) -> Dict:
        """Tool: Document operations."""
        operation = operation.lower()
        
        if operation == "create":
            result = await self.db.query(
                "CREATE document SET content=$content",
                {"content": content}
            )
            return {"created": result[0][0] if result else None}
        
        elif operation == "read":
            result = await self.db.query(
                "SELECT * FROM document WHERE id = $id",
                {"id": doc_id}
            )
            return {"document": result[0][0] if result and result[0] else None}
        
        elif operation == "update":
            result = await self.db.query(
                "UPDATE document SET content=$content WHERE id = $id",
                {"content": content, "id": doc_id}
            )
            return {"updated": result[0][0] if result else None}
        
        elif operation == "delete":
            result = await self.db.query(
                "DELETE FROM document WHERE id = $id",
                {"id": doc_id}
            )
            return {"deleted": True}
        
        elif operation == "list":
            result = await self.db.query("SELECT * FROM document LIMIT 50")
            return {"documents": result[0] if result else []}
        
        return {"error": f"Unknown operation: {operation}"}
    
    # ----- Query Tool -----
    
    async def query(self, sql: str, vars: Dict = None) -> Any:
        """Tool: Execute raw SurrealQL."""
        result = await self.db.query(sql, vars or {})
        return result[0] if result else []
    
    # ----- Schema Tool -----
    
    async def schema(self, operation: str, table: str = None,
                fields: Dict = None) -> Dict:
        """Tool: Schema operations."""
        operation = operation.lower()
        
        if operation == "create_table":
            field_defs = []
            for field, ftype in (fields or {}).items():
                field_defs.append(f"DEFINE FIELD {field} ON {table} TYPE {ftype}")
            
            await self.db.query(f"DEFINE TABLE {table} SCHEMAFULL;")
            for fd in field_defs:
                await self.db.query(fd)
            
            return {"created": table}
        
        elif operation == "list_tables":
            result = await self.db.query("INFO FOR DB;")
            return {"tables": result[0][0].get("tables", {}) if result and result[0] else {}}
        
        return {"error": f"Unknown operation: {operation}"}


# Singleton instance
_tools_instance = None

async def get_tools() -> SurrealDBTools:
    """Get tools instance."""
    global _tools_instance
    if _tools_instance is None:
        _tools_instance = SurrealDBTools()
        await _tools_instance.connect()
    return _tools_instance


# ----- Export as Functions -----

async def vector_search_tool(query: str, k: int = 5) -> List[Dict]:
    """Search by vector similarity."""
    tools = await get_tools()
    return await tools.vector_search(query, k=k)


async def knowledge_graph_tool(operation: str, entity: str = None, 
                       relation: str = None, to_entity: str = None) -> Dict:
    """Knowledge graph operations."""
    tools = await get_tools()
    return await tools.knowledge_graph(operation, entity, relation, to_entity)


async def rag_tool(question: str, k: int = 5) -> Dict:
    """RAG - retrieve and generate."""
    tools = await get_tools()
    return await tools.rag(question, k=k)


async def realtime_tool(operation: str, table: str = "message", 
                  query: str = None) -> Dict:
    """Real-time operations."""
    tools = await get_tools()
    return await tools.realtime(operation, table, query)


async def document_tool(operation: str, content: str = None,
                    doc_id: str = None) -> Dict:
    """Document CRUD operations."""
    tools = await get_tools()
    return await tools.document(operation, content, doc_id)


async def query_tool(sql: str, vars: Dict = None) -> Any:
    """Execute raw SurrealQL."""
    tools = await get_tools()
    return await tools.query(sql, vars)


async def schema_tool(operation: str, table: str = None,
               fields: Dict = None) -> Dict:
    """Schema operations."""
    tools = await get_tools()
    return await tools.schema(operation, table, fields)


# ----- Main Demo -----

async def demo():
    """Demo all tools."""
    print("🛠️ SurrealDB Tools Demo")
    print("="*40)
    
    tools = SurrealDBTools()
    await tools.connect()
    
    # Create schema
    print("\n📋 Creating table...")
    await tools.schema("create_table", "doc", {"content": "string", "embedding": "array<float>"})
    
    # Add document
    print("\n📄 Creating document...")
    doc = await tools.document("create", content="AI agents use memory")
    print(f"   Created: {doc['id']}")
    
    # RAG
    print("\n🔍 RAG search...")
    result = await rag_tool("memory in AI")
    print(f"   Found: {result.get('sources', [])}")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(demo())