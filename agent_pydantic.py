"""
Support agent using PydanticAI framework.

Same functionality as agent.py but using PydanticAI for
type-safe tool definitions and response validation.
"""

import os
import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from openai import AsyncOpenAI
from surrealdb import Surreal


# -- Configuration -----------------------------------------------------------

MODEL = "gpt-4.1-mini"
EMBED_MODEL = "text-embedding-3-small"

SYSTEM_PROMPT = """\
You are a support agent for the Acme Platform. You help customers resolve
technical issues by searching the knowledge base and exploring product
relationships.

IMPORTANT: For EVERY question, you MUST follow these steps in order:
1. ALWAYS call review_past_decisions first to check how similar queries
   were handled before. This is mandatory — never skip this step.
2. Search for relevant articles using semantic search.
3. Explore related products, tickets, and solutions using graph traversal.
4. Synthesise a clear, actionable answer with specific steps.

Always cite which articles or solutions you used. If you cannot find a
relevant answer, say so — do not make things up."""


# -- Pydantic Models -------------------------------------------------------


class SearchResult(BaseModel):
    id: str
    title: str
    category: str
    content: str
    distance: float | None = None


class ProductInfo(BaseModel):
    name: str
    description: str
    version: str


class RelatedEntity(BaseModel):
    title: str | None = None
    name: str | None = None
    category: str | None = None
    version: str | None = None
    tickets: list = []
    solutions: list = []


class Solution(BaseModel):
    title: str
    steps: str
    verified: bool


class PastDecision(BaseModel):
    query: str
    response: str
    model: str
    created: datetime
    similarity: float | None = None


# -- Database Clients ------------------------------------------------------

llm = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

db = Surreal("ws://localhost:8000/rpc")


async def init_db():
    await db.signin({"username": "root", "password": "root"})
    await db.use("demo", "support")


async def close_db():
    await db.close()


# -- Session tracking ----------------------------------------------------

session_data: dict = {}


async def new_session() -> str:
    sid = uuid.uuid4().hex[:8]
    session_data.update(
        sid=sid,
        step=0,
        query_emb=None,
    )
    return sid


# -- Helpers -------------------------------------------------------------


async def embed_text(text: str) -> list[float]:
    resp = await llm.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


def _rows(result) -> list:
    if not result:
        return []
    first = result[0]
    if isinstance(first, dict):
        return result
    if isinstance(first, list):
        return first
    return []


async def trace_decision(action: str, tool: str | None = None, result_summary: str | None = None):
    session_data["step"] += 1
    await db.query(
        f"""
        CREATE decision_step:{uuid.uuid4().hex[:8]} SET
        session = $sid,
        step = $step,
        action = $action,
        tool = $tool,
        result_summary = $result_summary;
        """,
        {
            "sid": session_data["sid"],
            "step": session_data["step"],
            "action": action,
            "tool": tool,
            "result_summary": result_summary,
        },
    )


# -- Tool Implementations -----------------------------------------------


async def search_articles(query: str, limit: int = 5) -> list[SearchResult]:
    """Semantic vector search over articles."""
    emb = await embed_text(query)
    result = await db.query(
        f"""
        SELECT id, title, category, content, vector::distance::knn() AS distance
        FROM article
        WHERE embedding <|{limit},100|> $emb;
        """,
        {"emb": emb},
    )
    rows = _rows(result)
    return [SearchResult(**{**r, "distance": r.get("distance")}) for r in rows]


async def find_related(record_id: str) -> RelatedEntity:
    """Explore an entity in the knowledge graph."""
    table = record_id.split(":")[0]
    
    queries = {
        "article": """
        SELECT title, category, content,
            ->references->product.{name, version} AS products,
            ->related_to->article.{title, category} AS related_articles
        FROM type::record($id);""",
        "product": """
        SELECT name, description, version,
            <-references<-article.{title, category} AS articles,
            <-about<-ticket.{subject, status, priority} AS tickets,
            ->depends_on->product.name AS depends_on
        FROM type::record($id);""",
    }
    
    query = queries.get(table, "SELECT * FROM type::record($id);")
    result = await db.query(query, {"id": record_id})
    rows = _rows(result)
    
    if rows:
        r = rows[0]
        return RelatedEntity(
            title=r.get("title"),
            name=r.get("name"),
            category=r.get("category"),
            version=r.get("version"),
            tickets=r.get("tickets", []),
            solutions=r.get("solutions", []),
        )
    return RelatedEntity()


async def find_solutions(product: str) -> dict:
    """Find known solutions for a product."""
    result = await db.query(
        """
        SELECT name,
            <-about<-ticket.{subject, status, priority} AS tickets,
            <-about<-ticket->resolved_by[
                WHERE weight > 0.5
                AND (valid_until IS NONE OR valid_until > time::now())
            ]->solution.{title, steps, verified} AS solutions,
            ->depends_on->product.name AS dependencies
        FROM type::record($product);
        """,
        {"product": product},
    )
    rows = _rows(result)
    if rows:
        r = rows[0]
        return {
            "name": r.get("name"),
            "tickets": r.get("tickets", []),
            "solutions": [Solution(**s) for s in r.get("solutions", [])],
            "dependencies": r.get("dependencies", []),
        }
    return {"name": product, "tickets": [], "solutions": [], "dependencies": []}


async def review_past_decisions(query: str, limit: int = 3) -> list[PastDecision]:
    """Search past agent sessions for similar queries."""
    emb = await embed_text(query)
    result = await db.query(
        f"""
        SELECT query, response, model, created,
            vector::distance::knn() AS similarity
        FROM response_trace
        WHERE query_embedding <|{limit},100|> $emb
        AND session != $current_session;
        """,
        {"emb": emb, "current_session": session_data["sid"]},
    )
    rows = _rows(result)
    return [PastDecision(**{**r, "similarity": r.get("similarity")}) for r in rows]


# -- PydanticAI Agent -----------------------------------------------

agent = Agent(
    model=MODEL,
    result_type=str,
    system_prompt=SYSTEM_PROMPT,
    tools=[
        search_articles,
        find_related,
        find_solutions,
        review_past_decisions,
    ],
)


async def main():
    await init_db()
    sid = await new_session()
    print(f"Session: {sid}")
    print("Type your question, or 'quit' to exit.")
    
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break
        
        await trace_decision(action="receive_query", result_summary=user_input)
        
        result = await agent.run(user_input)
        print(f"\nAgent: {result.data}")
        
        await trace_decision(action="answer", result_summary=result.data[:300])
    
    await close_db()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())