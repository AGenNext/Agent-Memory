"""
Support agent using LangGraph with enforced review-first flow.

Features:
- State machine with explicit review step
- Human-in-the-loop approval before final response
- Full conversation history in state
"""

import os
import uuid
from typing import TypedDict, Annotated
from operator import add

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

from surrealdb import Surreal


# -- Configuration -----------------------------------------------------------

MODEL = "gpt-4.1-mini"
EMBED_MODEL = "text-embedding-3-small"

SYSTEM_PROMPT = """\
You are a support agent for the Acme Platform. You help customers resolve
technical issues by searching the knowledge base and exploring product
relationships.

IMPORTANT: You must follow this workflow:
1. ALWAYS call review_past_decisions first to check similar past queries
2. Search for relevant articles using semantic search
3. Explore related products, tickets, and solutions
4. Synthesise a clear, actionable answer
5. Present answer for human review BEFORE responding

Always cite which articles or solutions you used."""


# -- State --------------------------------------------------------------

class AgentState(TypedDict):
    messages: Annotated[list, add]
    documents: list | None
    products: list | None
    solutions: list | None
    past_decisions: list | None
    review_needed: bool
    final_response: str | None


# -- Database Helpers --------------------------------------------------

from openai import AsyncOpenAI

db = Surreal("ws://localhost:8000/rpc")


async def init_db():
    await db.signin({"username": "root", "password": "root"})
    await db.use("demo", "support")


def _rows(result) -> list:
    if not result:
        return []
    first = result[0]
    if isinstance(first, dict):
        return result
    if isinstance(first, list):
        return first
    return []


async def embed_text(text: str) -> list[float]:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


# -- Tools -------------------------------------------------------------

async def search_articles(query: str, limit: int = 5) -> list[dict]:
    """Semantic vector search over articles."""
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    emb = await embed_text(query)
    
    result = await db.query(
        f"""
        SELECT id, title, category, content, vector::distance::knn() AS distance
        FROM article
        WHERE embedding <|{limit},100|> $emb;
        """,
        {"emb": emb},
    )
    return _rows(result)


async def find_related(record_id: str) -> list[dict]:
    """Explore an entity in the knowledge graph."""
    table = record_id.split(":")[0]
    queries = {
        "article": """
        SELECT title, category, content,
            ->references->product.{name, version} AS products
        FROM type::record($id);""",
        "product": """
        SELECT name, description, version,
            <-references<-article.{title, category} AS articles,
            <-about<-ticket.{subject, status, priority} AS tickets
        FROM type::record($id);""",
    }
    query = queries.get(table, "SELECT * FROM type::record($id);")
    result = await db.query(query, {"id": record_id})
    return _rows(result)


async def find_solutions(product: str) -> list[dict]:
    """Find known solutions for a product."""
    result = await db.query(
        """
        SELECT name,
            <-about<-ticket->resolved_by[
                WHERE weight > 0.5
            ]->solution.{title, steps, verified} AS solutions
        FROM type::record($product);
        """,
        {"product": product},
    )
    return _rows(result)


async def review_past_decisions(query: str, limit: int = 3) -> list[dict]:
    """Search past agent sessions for similar queries."""
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    emb = await embed_text(query)
    
    result = await db.query(
        f"""
        SELECT query, response, created,
            vector::distance::knn() AS similarity
        FROM response_trace
        WHERE query_embedding <|{limit},100|> $emb;
        """,
        {"emb": emb},
    )
    return _rows(result)


tools = [search_articles, find_related, find_solutions, review_past_decisions]
tool_node = ToolNode(tools)


# -- Graph Nodes ---------------------------------------------------------

llm = ChatOpenAI(model=MODEL, api_key=os.environ["OPENAI_API_KEY"])


async def should_continue(state: AgentState) -> str:
    """Decide if we need more reasoning or can respond."""
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    return "end"


async def call_model(state: AgentState):
    """Call the LLM with tools."""
    messages = state["messages"]
    response = await llm.bind_tools(tools).ainvoke(messages)
    return {"messages": [response]}


async def review_node(state: AgentState) -> AgentState:
    """Review step - human approval required before final response."""
    messages = state["messages"]
    last_message = messages[-1]
    
    # Mark that review is needed
    return {
        "review_needed": True,
        "final_response": last_message.content,
    }


async def approve_response(state: AgentState) -> AgentState:
    """Node that waits for human approval."""
    messages = state["messages"]
    last_message = messages[-1]
    
    print(f"\n=== REVIEW REQUIRED ===")
    print(f"Response: {last_message.content[:500]}")
    approval = input("\nApprove? (y/n): ").strip().lower()
    
    if approval == "y":
        print("Response approved!")
    else:
        print("Response rejected. Agent will try again.")
        messages.append({"role": "user", "content": "Please revise your response based on feedback."})
    
    return state


# -- Build Graph ---------------------------------------------------------

workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)
workflow.add_node("review", review_node)
workflow.add_node("approval", approve_response)

workflow.set_entry_point("agent")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "end": "review",
    }
)

workflow.add_edge("tools", "agent")
workflow.add_edge("review", "approval")
workflow.add_edge("approval", "agent")

workflow.add_edge("approval", END)

graph = workflow.compile()


async def main():
    await init_db()
    print("Session started")
    print("Type your question, or 'quit' to exit.")
    
    while True:
        user_input = input("\nYou: ").strip()
        if not user_input in ("quit", "exit", "q"):
            break
        
        initial_state = {
            "messages": [{"role": "user", "content": user_input}],
            "documents": None,
            "products": None,
            "solutions": None,
            "past_decisions": None,
            "review_needed": False,
            "final_response": None,
        }
        
        async for state in graph.astream(initial_state):
            if "agent" in state:
                print(f"\nAgent: {state['agent']['messages'][-1].content[:300]}")
        
        if state.get("final_response"):
            print(f"\n=== FINAL ===\n{state['final_response']}")
    
    await db.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())