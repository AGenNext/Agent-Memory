#!/usr/bin/env python3
"""
Sample Agent: Customer Support AI

Based on Verizon case study
- AI assistant for 10,000 technicians
- Real-time documentation access
- Outage updates and workflows
"""

import asyncio
from surrealdb import Surreal


class SupportAgent:
    """Customer support AI agent."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "support", "database": "agent"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Support schema."""
        schemas = [
            """
            DEFINE TABLE document SCHEMAFULL;
            DEFINE FIELD title ON document TYPE string;
            DEFINE FIELD content ON document TYPE string;
            DEFINE FIELD category ON document TYPE string;
            DEFINE FIELD embedding ON document TYPE array<float>;
            DEFINE FIELD updated ON document TYPE datetime;
            """,
            """
            DEFINE TABLE technician SCHEMAFULL;
            DEFINE FIELD name ON technician TYPE string;
            DEFINE FIELD region ON technician TYPE string;
            DEFINE FIELD skills ON technician TYPE array<string>;
            DEFINE FIELD active ON technician TYPE bool;
            """,
            """
            DEFINE TABLE ticket SCHEMAFULL;
            DEFINE FIELD technician ON ticket TYPE record(technician);
            DEFINE FIELD issue ON ticket TYPE string;
            DEFINE FIELD status ON ticket TYPE string;
            DEFINE FIELD priority ON ticket TYPE string;
            DEFINE FIELD created ON ticket TYPE datetime;
            """,
            """
            DEFINE TABLE outage SCHEMAFULL;
            DEFINE FIELD region ON outage TYPE string;
            DEFINE FIELD cause ON outage TYPE string;
            DEFINE FIELD status ON outage TYPE string;
            DEFINE FIELD estimated_fix ON outage TYPE datetime;
            """,
        ]
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Support schema created")
    
    # ----- Search Documentation -----
    
    async def search_docs(self, query: str, k: int = 5) -> list:
        """Search documentation."""
        result = await self.db.query(
            """SELECT * FROM document WHERE content @@ $query ORDER BY updated DESC LIMIT $k""",
            {"query": query, "k": k}
        )
        return result[0] if result else []
    
    # ----- Ticket Management -----
    
    async def create_ticket(self, technician_id: str, issue: str, priority: str = "medium") -> dict:
        """Create support ticket."""
        result = await self.db.query(
            """CREATE ticket SET technician=$tech, issue=$issue, status='open', priority=$priority, created=time::now()""",
            {"tech": technician_id, "issue": issue, "priority": priority}
        )
        return result[0][0]
    
    async def assign_ticket(self, ticket_id: str, technician_id: str) -> dict:
        """Assign ticket to technician."""
        result = await self.db.query(
            "UPDATE ticket SET technician=$tech WHERE id = $id",
            {"id": ticket_id, "tech": technician_id}
        )
        return result[0][0]
    
    # ----- Outage Tracking -----
    
    async def report_outage(self, region: str, cause: str) -> dict:
        """Report outage."""
        result = await self.db.query(
            """CREATE outage SET region=$region, cause=$cause, status='active', 
            estimated_fix=time::now() + 2h""",
            {"region": region, "cause": cause}
        )
        return result[0][0]
    
    async def get_outages(self) -> list:
        """Get active outages."""
        result = await self.db.query(
            "SELECT * FROM outage WHERE status = 'active'"
        )
        return result[0] if result else []
    
    # ----- AI Response -----
    
    async def answer_question(self, question: str) -> dict:
        """Answer technician question."""
        # Search docs
        docs = await self.search_docs(question)
        
        # Get outages
        outages = await self.get_outages()
        
        return {
            "question": question,
            "relevant_docs": docs[:3],
            "active_outages": outages[:2],
            "answer": "Based on documentation and current outages..."
        }


async def demo():
    """Demo support agent."""
    agent = SupportAgent()
    await agent.connect()
    await agent.setup_schema()
    
    # Ask question
    result = await agent.answer_question("How to fix network issue in region west?")
    print(f"Answer: {result}")


if __name__ == "__main__":
    asyncio.run(demo())