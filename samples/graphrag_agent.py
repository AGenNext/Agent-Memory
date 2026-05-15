#!/usr/bin/env python3
"""
Sample Agent: GraphRAG Chatbot

Based on: GraphRAG with SurrealDB + LangChain
- Vector search + Graph traversal
- Medical symptoms & treatments
- Hybrid retrieval
"""

import asyncio
from surrealdb import Surreal


class GraphRAGAgent:
    """GraphRAG chatbot agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "graphrag", "database": "medical"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """GraphRAG schema."""
        # Vector store for symptoms
        await self.db.query("""
            DEFINE TABLE symptom SCHEMAFULL;
            DEFINE FIELD name ON symptom TYPE string;
            DEFINE FIELD description ON symptom TYPE string;
            DEFINE FIELD category ON symptom TYPE string;
            DEFINE FIELD embedding ON symptom TYPE array<float>;
        """)
        
        # Graph store for treatments
        await self.db.query("""
            DEFINE TABLE treatment SCHEMAFULL;
            DEFINE FIELD name ON treatment TYPE string;
            DEFINE FIELD category ON treatment TYPE string;
        """)
        
        # Relations
        await self.db.query("""
            DEFINE TABLE treats TYPE RELATION FROM treatment TO symptom;
        """)
        
        await self.db.query("""
            DEFINE TABLE attends TYPE RELATION FROM treatment TO medical_practice;
        """)
        
        # Medical practice
        await self.db.query("""
            DEFINE TABLE medical_practice SCHEMAFULL;
            DEFINE FIELD name ON medical_practice TYPE string;
        """)
        
        # Index for vector search
        await self.db.query("""
            DEFINE INDEX symptom_vec ON symptom FIELDS embedding HNSW DIMENSION 384 DISTANCE COSINE;
        """)
        
        print("✅ GraphRAG schema created")
    
    # ----- Ingest Data -----
    
    async def add_symptom(self, name: str, description: str, 
                       category: str = "General") -> dict:
        """Add symptom to vector store."""
        result = await self.db.query(
            """CREATE symptom SET name=$name, description=$desc, category=$cat""",
            {"name": name, "desc": description, "cat": category}
        )
        return result[0][0]
    
    async def add_treatment(self, name: str, category: str = "medication") -> dict:
        """Add treatment."""
        result = await self.db.query(
            "CREATE treatment SET name=$name, category=$category",
            {"name": name, "category": category}
        )
        return result[0][0]
    
    async def add_practice(self, name: str) -> dict:
        """Add medical practice."""
        result = await self.db.query(
            "CREATE medical_practice SET name=$name",
            {"name": name}
        )
        return result[0][0]
    
    async def relate_treatment_to_symptom(self, treatment_id: str, symptom_id: str):
        """Create Treats relation."""
        result = await self.db.query(
            "RELATE treatment:$treatment -> treats -> symptom:$symptom",
            {"treatment": treatment_id, "symptom": symptom_id}
        )
        return result[0][0]
    
    async def relate_treatment_to_practice(self, treatment_id: str, practice_id: str):
        """Create Attends relation."""
        result = await self.db.query(
            "RELATE treatment:$treatment -> attends -> medical_practice:$practice",
            {"treatment": treatment_id, "symptom": practice_id}
        )
        return result[0][0]
    
    # ----- Vector Search -----
    
    async def search_symptoms(self, query: str, k: int = 3) -> list:
        """Search symptoms by similarity."""
        query_emb = [0.1] * 384  # Would use actual embeddings
        
        result = await self.db.query(f"""
            SELECT *, vector::distance::knn() AS score
            FROM symptom WHERE embedding <|{k}|> $emb
            ORDER BY score ASC
        """, {"emb": query_emb, "k": k})
        
        return result[0] if result else []
    
    # ----- Graph Query -----
    
    async def get_treatments_for_symptoms(self, symptoms: list) -> list:
        """Get treatments related to symptoms."""
        symptom_list = ", ".join([f'"{s}"' for s in symptoms])
        
        result = await self.db.query(f"""
            SELECT <-treats<-treatment.name AS treatment
            FROM symptom WHERE name IN [{symptom_list}]
        """)
        
        return result[0] if result else []
    
    async def get_practices_for_symptoms(self, symptoms: list) -> list:
        """Get medical practices for symptoms."""
        symptom_list = ", ".join([f'"{s}"' for s in symptoms])
        
        result = await self.db.query(f"""
            SELECT <-treats<-treatment->attends->medical_practice.name AS practice
            FROM symptom WHERE name IN [{symptom_list}]
        """)
        
        return result[0] if result else []
    
    # ----- Full RAG -----
    
    async def chat(self, user_symptoms: str) -> dict:
        """Process user query with GraphRAG."""
        # 1. Vector search
        symptoms = await self.search_symptoms(user_symptoms)
        
        # 2. Graph queries
        treatment_results = await self.get_treatments_for_symptoms(
            [s.get("name", "") for s in symptoms[:3]]
        )
        
        practice_results = await self.get_practices_for_symptoms(
            [s.get("name", "") for s in symptoms[:3]]
        )
        
        return {
            "user_query": user_symptoms,
            "found_symptoms": symptoms[:3],
            "treatments": treatment_results,
            "practices": practice_results,
            "response": "Based on your symptoms, consider..."
        }


async def demo():
    """Demo."""
    agent = GraphRAGAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Add sample data
    await agent.add_symptom(
        "Fever", 
        "Elevated body temperature above 100.4°F",
        "General"
    )
    await agent.add_treatment("Antipyretics")
    await agent.add_practice("General Practice")
    
    # Chat
    result = await agent.chat("I have a fever")
    print(f"Response: {result}")


if __name__ == "__main__":
    asyncio.run(demo())