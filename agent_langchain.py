"""
Support agent using LangChain framework.

Uses LangChain tools for SurrealDB integration.
"""

import os
import uuid
from typing import Optional

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain.prompts import ChatPrompt_template, MessagesPlaceholder


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


# -- Database Clients ------------------------------------------------------

from openai import AsyncOpenAI

llm = ChatOpenAI(model=MODEL, api_key=os.environ["OPENAI_API_KEY"])

db = Surreal("ws://localhost:8000/rpc")


async def init_db():
    await db.signin({"username": "root", "password": "root"})
    await db.use("demo", "support")


# -- Session tracking ----------------------------------------------------

session_data: dict = {}


async def new_session() -> str:
    sid = uuid.uuid4().hex[:8]
    session_data.update(sid=sid, step=0)
    return sid


async def embed_text(text: str) -> list[float]:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
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


# -- LangChain Tools ------------------------------------------------------


@tool
async def search_articles(query: str, limit: int = 5) -> str:
    """Semantic vector search over knowledge base articles.
    
    Args:
        query: Natural language search query
        limit: Max articles to return (default 5)
    """
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = await client.embeddings.create(model=EMBED_MODEL, input=query)
    emb = resp.data[0].embedding
    
    result = await db.query(
        f"""
        SELECT id, title, category, content, vector::distance::knn() AS distance
        FROM article
        WHERE embedding <|{limit},100|> $emb;
        """,
        {"emb": emb},
    )
    rows = _rows(result)
    import json
    return json.dumps(rows, indent=2, default=str)


@tool
async def find_related(record_id: str) -> str:
    """Explore an entity in the knowledge graph.
    
    Args:
        record_id: SurrealDB record ID (e.g. product:auth)
    """
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
    import json
    return json.dumps(rows, indent=2, default=str)


@tool
async def find_solutions(product: str) -> str:
    """Find known solutions for a product.
    
    Args:
        product: Product record ID (e.g. product:auth)
    """
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
    import json
    return json.dumps(rows, indent=2, default=str)


@tool
async def review_past_decisions(query: str, limit: int = 3) -> str:
    """Search past agent sessions for similar queries.
    
    Args:
        query: The query to find similar past decisions for
        limit: Max past responses to return (default 3)
    """
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = await client.embeddings.create(model=EMBED_MODEL, input=query)
    emb = resp.data[0].embedding
    
    result = await db.query(
        f"""
        SELECT query, response, model, created,
            vector::distance::knn() AS similarity
        FROM response_trace
        WHERE query_embedding <|{limit},100|> $emb
        AND session != $current_session;
        """,
        {"emb": emb, "current_session": session_data.get("sid", "")},
    )
    rows = _rows(result)
    import json
    return json.dumps(rows, indent=2, default=str)


# -- Agent ---------------------------------------------------------------

tools = [search_articles, find_related, find_solutions, review_past_decisions]

prompt = ChatPrompt_template.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


async def main():
    await init_db()
    sid = await new_session()
    print(f"Session: {sid}")
    print("Type your question, or 'quit' to exit.")
    
    chat_history = []
    
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break
        
        result = agent_executor.invoke({
            "input": user_input,
            "chat_history": chat_history,
        })
        
        response = result["output"]
        print(f"\nAgent: {response}")
        
        chat_history.extend([
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": response},
        ])
    
    await db.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())