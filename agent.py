"""
Support agent backed by a knowledge graph in SurrealDB.

Uses OpenAI for model access and SurrealDB for vector search + graph
traversal over a support knowledge base.

Every reasoning step, retrieval, and response is traced as graph and
timeseries entries in SurrealDB — enabling decision auditing,
retrieval analysis, and response comparison over time.
"""

import json
import os
import uuid

from openai import OpenAI
from surrealdb import Surreal
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


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


# -- Clients -----------------------------------------------------------------

llm = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

db = Surreal("ws://localhost:8000/rpc")
db.signin({"username": "root", "password": "root"})
db.use("demo", "support")

console = Console()


# -- Session tracking --------------------------------------------------------

session: dict = {}


def new_session() -> str:
    """Start a fresh tracing session and return its ID."""
    sid = uuid.uuid4().hex[:8]
    session.update(
        sid=sid,
        step=0,
        prev_step_id=None,
        query_emb=None,
        pending_retrieval=None,
    )
    return sid


# -- Helpers -----------------------------------------------------------------


def embed_text(text: str) -> list[float]:
    return llm.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding


def _rows(result) -> list:
    """Normalize a query result to a list of row dicts."""
    if not result:
        return []
    first = result[0]
    if isinstance(first, dict):
        return result
    if isinstance(first, list):
        return first
    return []


def _make_id() -> str:
    """Generate a short unique ID for trace records."""
    return uuid.uuid4().hex[:12]


def _summarize(fn_name: str, raw: str) -> str:
    """Build a concise summary of a tool's output for the decision trace."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw[:200]
    if not data:
        return "No results"
    if fn_name == "search_articles":
        titles = [r.get("title", "?") for r in data]
        return f"Found {len(data)} articles: {', '.join(titles)}"
    if fn_name == "find_solutions":
        r = data[0]
        n = r.get("name", "?")
        return f"{n}: {len(r.get('tickets') or [])} tickets, {len(r.get('solutions') or [])} solutions"
    if fn_name == "find_related":
        return f"Explored entity — {len(data[0])} fields returned"
    if fn_name == "review_past_decisions":
        return f"Found {len(data)} similar past queries"
    return raw[:200]


# -- Tracing -----------------------------------------------------------------


def trace_decision(
    action: str,
    tool: str | None = None,
    tool_args: dict | None = None,
    result_summary: str | None = None,
) -> str:
    """Record a decision step and chain it to the previous one via led_to."""
    session["step"] += 1
    rid = f"decision_step:{_make_id()}"
    db.query(
        f"""
        CREATE {rid} SET
        session = $sid,
        step = $step,
        action = $action,
        tool = $tool,
        tool_args = $tool_args,
        result_summary = $result_summary;
        """,
        {
            "sid": session["sid"],
            "step": session["step"],
            "action": action,
            "tool": tool,
            "tool_args": tool_args,
            "result_summary": result_summary,
        },
    )

    prev = session["prev_step_id"]
    if prev:
        db.query(f"RELATE {prev}->led_to->{rid};")

    session["prev_step_id"] = rid
    return rid


def flush_retrieval(step_rid: str):
    """Write a pending retrieval trace and link it to the owning decision step."""
    rt = session.get("pending_retrieval")
    if not rt:
        return
    session["pending_retrieval"] = None

    trid = f"retrieval_trace:{_make_id()}"
    db.query(
        f"""
        CREATE {trid} SET
        session = $sid,
        method = $method,
        query_text = $query_text,
        query_embedding = $emb,
        entity_ids = $entity_ids,
        distances = $distances;
        """,
        {
            "sid": session["sid"],
            "method": rt["method"],
            "query_text": rt["query_text"],
            "emb": rt.get("emb"),
            "entity_ids": rt["entity_ids"],
            "distances": rt.get("distances"),
        },
    )

    db.query(f"RELATE {step_rid}->retrieved->{trid};")
    for eid in rt["entity_ids"]:
        db.query(
            f"LET $e = type::record($eid); RELATE {trid}->used->$e;",
            {"eid": eid},
        )


def trace_response(query: str, emb: list[float], response_text: str,
                 token_count: int | None = None):
    """Record the final LLM response for comparison over time."""
    rrid = f"response_trace:{_make_id()}"
    db.query(
        f"""
        CREATE {rrid} SET
        session = $sid,
        query = $query,
        query_embedding = $emb,
        response = $response,
        model = $model,
        token_count = $tokens;
        """,
        {
            "sid": session["sid"],
            "query": query,
            "emb": emb,
            "response": response_text,
            "model": MODEL,
            "tokens": token_count,
        },
    )

    prev = session["prev_step_id"]
    if prev:
        db.query(f"RELATE {prev}->produced->{rrid};")


# -- Tool schemas (OpenAI function-calling format) ---------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_articles",
            "description": (
                "Semantic vector search over knowledge base articles. "
                "Returns the most relevant articles for a natural-language query."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max articles to return (default 5)",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_related",
            "description": (
                "Explore an entity in the knowledge graph. Given a record ID "
                "(e.g. product:auth, article:auth_setup, customer:northwind), "
                "returns its fields and all directly connected entities."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "record_id": {
                        "type": "string",
                        "description": "SurrealDB record ID (e.g. product:auth)",
                    },
                },
                "required": ["record_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_solutions",
            "description": (
                "Find known solutions for a product by traversing the graph: "
                "product ← tickets → solutions. Only returns currently valid, "
                "high-confidence solutions (filters by weight and time validity)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {
                        "type": "string",
                        "description": "Product record ID (e.g. product:auth)",
                    },
                },
                "required": ["product"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_past_decisions",
            "description": (
                "Search past agent sessions for similar queries. Returns "
                "previous responses and the decisions the agent made, so you "
                "can maintain consistency across sessions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query to find similar past decisions for",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max past responses to return (default 3)",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


# -- Tool implementations (each runs SurrealQL) ------------------------------


def search_articles(query: str, limit: int = 5) -> str:
    emb = embed_text(query)
    result = db.query(
        f"""
        SELECT id, title, category, content, vector::distance::knn() AS distance
        FROM article
        WHERE embedding <|{limit},100|> $emb;
        """,
        {"emb": emb},
    )
    rows = _rows(result)
    session["pending_retrieval"] = {
        "method": "vector",
        "query_text": query,
        "emb": emb,
        "entity_ids": [str(r["id"]) for r in rows],
        "distances": [r["distance"] for r in rows if r.get("distance") is not None],
    }
    return json.dumps(rows, indent=2, default=str)


def find_related(record_id: str) -> str:
    table = record_id.split(":")[0]
    queries = {
        "article": """
        SELECT
            title, category, content,
            ->references->product.{name, version} AS products,
            ->related_to->article.{title, category} AS related_articles
        FROM type::record($id);
        """,
        "product": """
        SELECT
            name, description, version,
            <-references<-article.{title, category} AS articles,
            <-about<-ticket.{subject, status, priority} AS tickets,
            ->depends_on->product.{name, version} AS depends_on,
            <-depends_on<-product.{name, version} AS depended_on_by
        FROM type::record($id);
        """,
        "customer": """
        SELECT
            name, email, plan,
            ->authored->ticket.{subject, status, priority, created} AS tickets
        FROM type::record($id);
        """,
        "ticket": """
        SELECT
            subject, description, status, priority, created,
            ->about->product.{name, version} AS products,
            ->resolved_by[WHERE weight > 0.5
            AND (valid_until IS NONE OR valid_until > time::now())]
            ->solution.{title, steps, verified} AS solutions,
            <-authored<-customer.{name, plan} AS filed_by
        FROM type::record($id);
        """,
        "solution": """
        SELECT
            title, steps, verified,
            <-resolved_by<-ticket.{subject, status} AS resolved_tickets
        FROM type::record($id);
        """,
    }
    query = queries.get(table, "SELECT * FROM type::record($id);")
    result = db.query(query, {"id": record_id})
    rows = _rows(result)
    session["pending_retrieval"] = {
        "method": "graph",
        "query_text": f"explore {record_id}",
        "entity_ids": [record_id],
    }
    return json.dumps(rows, indent=2, default=str)


def find_solutions(product: str) -> str:
    result = db.query(
        """
        SELECT
            name,
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
    session["pending_retrieval"] = {
        "method": "graph",
        "query_text": f"solutions for {product}",
        "entity_ids": [product],
    }
    return json.dumps(rows, indent=2, default=str)


def review_past_decisions(query: str, limit: int = 3) -> str:
    emb = embed_text(query)
    result = db.query(
        f"""
        SELECT
            query, response, model, created,
            vector::distance::knn() AS similarity
        FROM response_trace
        WHERE query_embedding <|{limit},100|> $emb
        AND session != $current_session;
        """,
        {"emb": emb, "current_session": session["sid"]},
    )
    rows = _rows(result)
    return json.dumps(rows, indent=2, default=str)


TOOL_DISPATCH = {
    "search_articles": search_articles,
    "find_related": find_related,
    "find_solutions": find_solutions,
    "review_past_decisions": review_past_decisions,
}


# -- Agent loop --------------------------------------------------------------


def run_agent(user_message: str, history: list[dict]) -> str:
    history.append({"role": "user", "content": user_message})

    query_emb = embed_text(user_message)
    session["query_emb"] = query_emb

    trace_decision(action="receive_query", result_summary=user_message)

    rounds = 0
    while True:
        rounds += 1
        if rounds > 15:
            return "Reached maximum reasoning rounds. Please try a simpler question."

        response = llm.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            tools=TOOLS,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or choice.message.tool_calls:
            history.append(choice.message)

            for call in choice.message.tool_calls:
                fn_name = call.function.name
                fn_args = json.loads(call.function.arguments)

                console.print(
                    Panel(
                        f"[bold]{fn_name}[/bold]({json.dumps(fn_args)})",
                        title="Tool Call",
                        border_style="cyan",
                    )
                )

                fn = TOOL_DISPATCH.get(fn_name)
                if fn:
                    result = fn(**fn_args)
                else:
                    result = json.dumps({"error": f"Unknown tool: {fn_name}"})

                summary = _summarize(fn_name, result)
                step_id = trace_decision(
                    action="tool_call",
                    tool=fn_name,
                    tool_args=fn_args,
                    result_summary=summary,
                )
                flush_retrieval(step_id)

                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": result,
                    }
                )
        else:
            answer = choice.message.content or ""
            history.append({"role": "assistant", "content": answer})

            trace_decision(action="answer", result_summary=answer[:300])
            trace_response(
                query=user_message,
                emb=query_emb,
                response_text=answer,
                token_count=response.usage.completion_tokens if response.usage else None,
            )

            return answer


# -- Interactive chat --------------------------------------------------------


def main():
    sid = new_session()

    console.print(
        Panel(
            "[bold]Acme Platform Support Agent[/bold]\n"
            f"Model: {MODEL} via OpenAI\n"
            "Memory: SurrealDB knowledge graph + vectors\n"
            f"Session: {sid} (all decisions traced)\n\n"
            "Type your question, or 'quit' to exit.",
            border_style="green",
        )
    )

    history: list[dict] = []

    while True:
        console.print()
        user_input = console.input("[bold green]You:[/bold green] ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break

        answer = run_agent(user_input, history)

        console.print()
        console.print(Panel(Markdown(answer), title="Agent", border_style="blue"))


if __name__ == "__main__":
    main()