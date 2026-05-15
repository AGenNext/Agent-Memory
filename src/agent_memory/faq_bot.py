"""
FAQ Bot - Answer questions from SurrealDB documentation.

This bot uses Agent Memory to store FAQ entries and answer user questions
using semantic search and LLM context.
"""

import asyncio
import uuid

from surrealdb import Surreal
from openai import AsyncOpenAI
from pydantic import BaseModel


class FAQEntry(BaseModel):
    """A FAQ entry."""
    id: str
    question: str
    answer: str
    category: str
    tags: list[str] = []


class FAQBot:
    """
    FAQ Bot - Answer questions using knowledge base.
    
    Example:
        bot = FAQBot(db, llm)
        
        # Add FAQ entries
        await bot.add_faq(
            question="How do I install SurrealDB?",
            answer="Use: curl -sSf https://install.surrealdb.com | sh",
            category="installation"
        )
        
        # Answer question
        answer = await bot.ask("How to install?")
        print(answer)
    """
    
    def __init__(self, db: Surreal, llm: AsyncOpenAI):
        self.db = db
        self.llm = llm
    
    async def add_faq(
        self,
        question: str,
        answer: str,
        category: str,
        tags: list[str] = None,
    ) -> str:
        """Add a FAQ entry."""
        fid = f"faq:{uuid.uuid4().hex[:8]}"
        
        await self.db.query(
            f"""CREATE {fid} SET
                question = $question,
                answer = $answer,
                category = $category,
                tags = $tags,
                created = time::now();""",
            {
                "question": question,
                "answer": answer,
                "category": category,
                "tags": tags or [],
            },
        )
        
        return fid
    
    async def add_faqs(self, faqs: list[dict]) -> int:
        """Add multiple FAQs at once."""
        count = 0
        for faq in faqs:
            await self.add_faq(
                question=faq["question"],
                answer=faq["answer"],
                category=faq.get("category", "general"),
                tags=faq.get("tags", []),
            )
            count += 1
        return count
    
    async def search_faqs(self, query: str, limit: int = 5) -> list[dict]:
        """Search FAQs by keyword."""
        result = await self.db.query(
            f"""SELECT * FROM faq 
                WHERE question CONTAINS $query 
                OR answer CONTAINS $query
                LIMIT $limit;""",
            {"query": query, "limit": limit},
        )
        
        if not result:
            return []
        
        return result[0] if result else []
    
    async def get_by_category(self, category: str) -> list[dict]:
        """Get all FAQs in a category."""
        result = await self.db.query(
            "SELECT * FROM faq WHERE category = $category;",
            {"category": category},
        )
        
        if not result:
            return []
        
        return result[0] if result else []
    
    async def ask(self, question: str) -> str:
        """
        Answer a question using the FAQ knowledge base.
        
        Uses LLM to find relevant FAQs and generate answer.
        """
        # Search relevant FAQs
        faqs = await self.search_faqs(question, limit=5)
        
        if not faqs:
            # Try broader search
            faqs = await self.search_faqs("", limit=10)
        
        if not faqs:
            return "I don't have information about that in my FAQ database."
        
        # Build context
        context = "\n\n".join([
            f"Q: {f['question']}\nA: {f['answer']}"
            for f in faqs
        ])
        
        # Ask LLM
        response = await self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a helpful FAQ bot. Answer user questions based on the provided FAQ entries.
If the question is answered in the FAQs, provide the answer. If not, say you don't know.

FAQ Entries:
{context}

Always be helpful and concise."""
                },
                {"role": "user", "content": question}
            ],
        )
        
        return response.choices[0].message.content
    
    async def get_categories(self) -> list[str]:
        """Get all FAQ categories."""
        result = await self.db.query(
            "SELECT category FROM faq GROUP BY category;"
        )
        
        if not result or not result[0]:
            return []
        
        return [r["category"] for r in result[0]]


# -- Default SurrealDB FAQs --

DEFAULT_FAQS = [
    # Installation
    {
        "question": "How do I install SurrealDB on Linux?",
        "answer": "Run: curl -sSf https://install.surrealdb.com | sh",
        "category": "installation",
        "tags": ["install", "linux", "setup"]
    },
    {
        "question": "How do I install SurrealDB on macOS?",
        "answer": "Use Homebrew: brew install surrealdb/tap/surreal",
        "category": "installation",
        "tags": ["install", "macos", "homebrew"]
    },
    {
        "question": "How do I install SurrealDB on Windows?",
        "answer": "Run: iwr https://windows.surrealdb.com -useb | iex",
        "category": "installation",
        "tags": ["install", "windows", "powershell"]
    },
    {
        "question": "How do I start SurrealDB?",
        "answer": "Run: surreal start --user root --pass root memory",
        "category": "installation",
        "tags": ["start", "run", "quickstart"]
    },
    
    # Configuration
    {
        "question": "How do I connect to SurrealDB from Python?",
        "answer": """Use the SDK:
from surrealdb import Surreal
db = Surreal('ws://localhost:8000/rpc')
await db.connect()
await db.use({'namespace': 'memory', 'database': 'agent'})
await db.signin({'username': 'root', 'password': 'root'})""",
        "category": "configuration",
        "tags": ["python", "sdk", "connect"]
    },
    {
        "question": "What are the storage engine options?",
        "answer": "Options: memory (in-memory), rocksdb (file), surrealkv (file), tikv (distributed)",
        "category": "configuration",
        "tags": ["storage", "engine", "rocksdb", "surrealkv"]
    },
    
    # Data Types
    {
        "question": "What data types does SurrealDB support?",
        "answer": "SurrealDB supports: string, int, float, bool, datetime, duration, array, object, record, geometry, uuid",
        "category": "data-types",
        "tags": ["types", "data", "schema"]
    },
    
    # Queries
    {
        "question": "How do I create a record in SurrealDB?",
        "answer": "Use CREATE: CREATE user SET name = 'Alice', role = 'admin';",
        "category": "queries",
        "tags": ["create", "insert", "sql"]
    },
    {
        "question": "How do I do a full-text search?",
        "answer": """1. Create index: DEFINE INDEX search ON article FIELDS content SEARCH ANALYZER simple BM25;
2. Search: SELECT * FROM article WHERE content @1@ 'search term';""",
        "category": "queries",
        "tags": ["search", "fulltext", "bm25"]
    },
    {
        "question": "How do I do vector search?",
        "answer": """1. Add embedding: CREATE article SET embedding = [0.1, 0.2, 0.3];
2. Create index: DEFINE INDEX vec ON article FIELDS embedding HNSW DIMENSION 512;
3. Search: SELECT * FROM article WHERE embedding <|5|> $query;""",
        "category": "queries",
        "tags": ["vector", "embedding", "similarity", "ai"]
    },
    {
        "question": "How do I use LIVE queries?",
        "answer": "Use LIVE SELECT: LIVE SELECT * FROM session WHERE status = 'active'; This subscribes to real-time changes.",
        "category": "queries",
        "tags": ["live", "realtime", "subscribe"]
    },
    
    # Graph
    {
        "question": "How do I create relationships in SurrealDB?",
        "answer": "Use RELATE: RELATE user:alice -> wrote -> article:intro; This creates a graph edge.",
        "category": "graph",
        "tags": ["graph", "relate", "relationship", "edge"]
    },
    {
        "question": "How do I traverse relationships?",
        "answer": "Use graph syntax: SELECT <-authored<-article FROM user:alice; This traverses from user to their articles.",
        "category": "graph",
        "tags": ["traverse", "query", "path"]
    },
    
    # Security
    {
        "question": "How do I create users and permissions?",
        "answer": "Use DEFINE USER and DEFINE ROLE: DEFINE USER alice ON DATABASE PASSWORD 'pass'; DEFINE ROLE admin PERMISSIONS FULL;",
        "category": "security",
        "tags": ["auth", "user", "role", "permission"]
    },
    
    # Performance
    {
        "question": "How do I create indexes?",
        "answer": "Use DEFINE INDEX: DEFINE INDEX email ON user COLUMNS email UNIQUE;",
        "category": "performance",
        "tags": ["index", "performance", "optimize"]
    },
    {
        "question": "How do I optimize queries?",
        "answer": "Use SELECT with specific fields, add indexes, use LIMIT, avoid SELECT * on large tables.",
        "category": "performance",
        "tags": ["optimize", "query", "performance"]
    },
    
    # Docker
    {
        "question": "How do I run SurrealDB with Docker?",
        "answer": "Run: docker run -p 8000:8000 surrealdb/surrealdb:latest start --user root --pass root memory",
        "category": "docker",
        "tags": ["docker", "container", "run"]
    },
    {
        "question": "How do I use Docker Compose?",
        "answer": """Create docker-compose.yml:
services:
  surrealdb:
    image: surrealdb/surrealdb:latest
    ports:
      - "8000:8000"
    command: start --user root --pass root memory""",
        "category": "docker",
        "tags": ["docker", "compose", "orchestration"]
    },
    
    # Tools
    {
        "question": "What tools are available for SurrealDB?",
        "answer": "Surrealist (UI), SurrealKit (migrations), SurrealML (in-db ML), CLI tools",
        "category": "tools",
        "tags": ["tools", "ui", "migrations", "ml"]
    },
    {
        "question": "How do I use Surrealist?",
        "answer": "Run: docker-compose up -d surrealist, then open http://localhost:3000",
        "category": "tools",
        "tags": ["surrealist", "ui", "visual"]
    },
    
    # Troubleshooting
    {
        "question": "Why can't I connect to SurrealDB?",
        "answer": "Check: 1) SurrealDB is running, 2) Correct port (default 8000), 3) Correct credentials, 4) Firewall settings",
        "category": "troubleshooting",
        "tags": ["connect", "error", "debug"]
    },
    {
        "question": "How do I check SurrealDB version?",
        "answer": "Run: surreal version",
        "category": "troubleshooting",
        "tags": ["version", "debug"]
    },
]


# -- Demo --

async def demo():
    """Demo the FAQ bot."""
    from agent_memory import AgentMemory, Config
    
    config = Config()
    memory = AgentMemory(config)
    await memory.connect()
    
    llm = AsyncOpenAI()
    
    bot = FAQBot(memory._db, llm)
    
    # Add default FAQs
    print("=== Adding FAQs ===")
    count = await bot.add_faqs(DEFAULT_FAQS)
    print(f"Added {count} FAQs")
    
    # Show categories
    cats = await bot.get_categories()
    print(f"Categories: {cats}")
    
    # Ask questions
    print("\n=== FAQ Bot Demo ===")
    
    questions = [
        "How do I install SurrealDB?",
        "How do I do vector search?",
        "What tools are available?",
        "How do I create relationships?",
    ]
    
    for q in questions:
        print(f"\nQ: {q}")
        answer = await bot.ask(q)
        print(f"A: {answer}")
    
    await memory.close()


if __name__ == "__main__":
    asyncio.run(demo())