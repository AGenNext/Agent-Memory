#!/usr/bin/env python3
"""
Quick Demo Runner - Run SurrealDB demos instantly

Usage:
    python3 demo.py              # Run all demos
    python3 demo.py 1           # Run specific demo
    python3 demo.py 2           # Vector demo
    python3 demo.py 3           # Agent memory demo
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

DEMOS = """
╔══════════════════════════════════════════════════════════════╗
║          Agent Memory Demos - Choose One!                  ║
╠══════════════════════════════════════════════════════════════╣
║  1. Basic CRUD      - Create, read, update, delete           ║
║  2. Vector Search  - Embeddings & similarity             ║
║  3. Agent Memory   - Sessions, entities, decisions      ║
║  4. Graph          - Relationships & traversal         ║
║  5. Live Queries   - Real-time subscriptions           ║
║  6. Full RAG       - Hybrid search with LLM            ║
║  a. All Demos      - Run everything                     ║
╚══════════════════════════════════════════════════════════╝
"""

def print_banner(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


async def demo1_crud():
    """Basic CRUD operations"""
    print_banner("Demo 1: Basic CRUD")
    
    from surrealdb import Surreal
    
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    # CREATE
    print("CREATE user SET name = 'Alice', role = 'admin'")
    await db.query("CREATE user SET name = 'Alice', role = 'admin'")
    
    # CREATE more
    await db.query("CREATE user SET name = 'Bob', role = 'user'")
    await db.query("CREATE user SET name = 'Charlie', role = 'developer'")
    
    # SELECT
    print("\nSELECT * FROM user:")
    result = await db.query("SELECT * FROM user")
    for r in result[0] if result else []:
        print(f"  - {r.get('id')}: {r.get('name')} ({r.get('role')})")
    
    # UPDATE
    print("\nUPDATE user SET role = 'superadmin' WHERE name = 'Alice'")
    await db.query("UPDATE user SET role = 'superadmin' WHERE name = 'Alice'")
    
    # SELECT again
    result = await db.query("SELECT * FROM user WHERE name = 'Alice'")
    print(f"  Alice is now: {result[0][0].get('role') if result and result[0] else 'N/A'}")
    
    # DELETE
    print("\nDELETE user WHERE name = 'Charlie'")
    await db.query("DELETE FROM user WHERE name = 'Charlie'")
    
    print("\n✅ CRUD complete!")
    await db.close()


async def demo2_vectors():
    """Vector search demo"""
    print_banner("Demo 2: Vector Search")
    
    try:
        from surrealdb import Surreal
        from openai import AsyncOpenAI
    except ImportError:
        print("❌ Install dependencies: pip install surrealdb openai")
        return
    
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    llm = AsyncOpenAI()
    
    # Create articles with embeddings
    articles = [
        ("AI Agent Memory", "How to build persistent memory for AI agents using knowledge graphs"),
        ("Vector Search", "Similarity search with embeddings for RAG applications"),
        ("Graph Database", "Relationship modeling and graph traversal queries"),
    ]
    
    print("Creating articles with embeddings...")
    for title, content in articles:
        emb = (await llm.embeddings.create(
            model="text-embedding-3-small",
            input=content
        )).data[0].embedding
        
        await db.query(
            "CREATE article SET title = $title, content = $content, embedding = $emb",
            {"title": title, "content": content, "emb": emb}
        )
        print(f"  ✅ {title}")
    
    # Search
    query = "persist memory for AI"
    q_emb = (await llm.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )).data[0].embedding
    
    print(f"\nSearching for: '{query}'")
    results = await db.query(
        """SELECT title, vector::distance::knn() AS dist
        FROM article WHERE embedding <|3|> $q
        ORDER BY dist ASC""",
        {"q": q_emb}
    )
    
    if results and results[0]:
        print("Results:")
        for r in results[0]:
            print(f"  - {r.get('title')}: {r.get('dist'):.4f}")
    else:
        print("  No results found (may need index)")
    
    print("\n✅ Vector search complete!")
    await db.close()


async def demo3_agent_memory():
    """Agent memory pattern"""
    print_banner("Demo 3: Agent Memory")
    
    import uuid
    from surrealdb import Surreal
    
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    session_id = f"session:{uuid.uuid4().hex[:8]}"
    print(f"Session: {session_id}")
    
    # Create session
    await db.query(f"""
        CREATE {session_id} SET 
        user_id = 'user:demo',
        status = 'active'
    """)
    
    # Add entities
    entities = [
        ("person", "Alice", {"email": "alice@test.com", "team": "engineering"}),
        ("person", "Bob", {"email": "bob@test.com", "team": "product"}),
        ("project", "Agent Memory", {"status": "in-progress"}),
    ]
    
    print("\nAdding entities...")
    for etype, name, props in entities:
        await db.query(
            "CREATE entity SET session = $sess, type = $type, name = $name, properties = $props",
            {"sess": session_id, "type": etype, "name": name, "props": props}
        )
        print(f"  ✅ {etype}: {name}")
    
    # Track decisions
    decisions = [
        ("search", "article", "Found docs on memory"),
        ("read", "entity", "Loaded user profiles"),
        ("reason", "llm", "Built context"),
    ]
    
    print("\nTracing decisions...")
    for action, tool, result in decisions:
        await db.query(
            "CREATE decision SET session = $sess, action = $action, tool = $tool, result = $result",
            {"sess": session_id, "action": action, "tool": tool, "result": result}
        )
        print(f"  ✅ {action} @ {tool}")
    
    # Get full context
    print("\nRetrieving context...")
    ctx = await db.query(f"""
        SELECT 
            (SELECT * FROM entity WHERE session = $sess) AS entities,
            (SELECT * FROM decision WHERE session = $sess ORDER BY created ASC) AS decisions
        FROM {session_id}
    """, {"sess": session_id})
    
    if ctx and ctx[0]:
        data = ctx[0][0]
        ents = data.get('entities', [])
        decs = data.get('decisions', [])
        print(f"  📦 {len(ents)} entities, {len(decs)} decisions")
    
    print("\n✅ Agent memory complete!")
    await db.close()


async def demo4_graph():
    """Graph relationships"""
    print_banner("Demo 4: Graph")
    
    from surrealdb import Surreal
    
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    # Create entities
    print("Creating knowledge graph...")
    await db.query("CREATE entity openai SET name = 'OpenAI', type = 'org'")
    await db.query("CREATE entity gpt4 SET name = 'GPT-4', type = 'model'")
    await db.query("CREATE entity anthropic SET name = 'Anthropic', type = 'org'")
    await db.query("CREATE entity claude SET name = 'Claude', type = 'model'")
    
    # Create relationships
    await db.query("RELATE entity:openai -> developed -> entity:gpt4")
    await db.query("RELATE entity:anthropic -> developed -> entity:claude")
    await db.query("RELATE entity:openai -> competes_with -> entity:anthropic")
    
    # Traverse
    print("\nTraversal examples:")
    
    # What did OpenAI develop?
    result = await db.query("SELECT ->developed->entity.name AS developed FROM entity:openai")
    print(f"  OpenAI developed: {result[0][0].get('developed') if result and result[0] else 'N/A'}")
    
    # Who developed what?
    result = await db.query("SELECT <-developed<-entity->developed->entity.name AS org, model FROM entity:model")
    print(f"  Organizations: {[r.get('org') for r in result[0]] if result and result[0] else []}")
    
    print("\n✅ Graph complete!")
    await db.close()


async def demo5_live():
    """LIVE queries"""
    print_banner("Demo 5: LIVE Queries")
    print("""
This demo requires TWO terminals:

Terminal 1 (subscriber):
    LIVE SELECT * FROM message;
    
Terminal 2 (publisher):
    CREATE message SET content = 'Hello!';
    
Watch the message appear in Terminal 1!

In Python, use:
    async for change in db.listen():
        print(change)
""")


async def demo6_rag():
    """Full RAG pipeline"""
    print_banner("Demo 6: Full RAG")
    
    try:
        from surrealdb import Surreal
        from openai import AsyncOpenAI
    except ImportError:
        print("❌ Install: pip install surrealdb openai")
        return
    
    db = Surreal('ws://localhost:8000/rpc')
    await db.connect()
    await db.use({'namespace': 'memory', 'database': 'agent'})
    await db.signin({'username': 'root', 'password': 'root'})
    
    llm = AsyncOpenAI()
    query = "how to configure access control"
    
    # Search both ways
    print(f"Query: '{query}'\n")
    
    # Embed query
    q_emb = (await llm.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )).data[0].embedding
    
    # Hybrid search  
    results = await db.query("""
        LET $q = $query;
        LET $emb = $embedding;
        
        LET $vs = SELECT id, title, 
            vector::similarity::cosine(embedding, $emb) AS score
        FROM document WHERE embedding <|10|> $emb
        ORDER BY score DESC LIMIT 5;
        
        LET $ft = SELECT id, title, search::score(1) AS score
        FROM document WHERE content @1@ $q
        ORDER BY score DESC LIMIT 5;
        
        SELECT * FROM search::rrf([$vs, $ft], 5, 60)
        LIMIT 5;
    """, {"query": query, "embedding": q_emb})
    
    print("Results:")
    if results and results[0]:
        for r in results[0][:3]:
            print(f"  - {r.get('title')}: rrf={r.get('rrf_score', 0):.3f}")
    else:
        print("  (No documents - run vector demo first to add data)")
    
    print("\n✅ RAG complete!")
    await db.close()


async def run_all():
    """Run all demos"""
    print(DEMOS)
    
    demos = [
        ("Basic CRUD", demo1_crud),
        ("Agent Memory", demo3_agent_memory),
        ("Graph", demo4_graph),
        ("Vectors", demo2_vectors),
        ("RAG", demo6_rag),
    ]
    
    for name, func in demos:
        try:
            await func()
        except Exception as e:
            print(f"❌ {name}: {e}")
    
    print("\n" + "="*60)
    print("  All demos complete!")
    print("="*60)


async def main():
    if len(sys.argv) < 2:
        print(DEMOS)
        choice = input("\nChoose demo: ").strip()
    else:
        choice = sys.argv[1]
    
    demos = {
        "1": demo1_crud,
        "2": demo2_vectors,
        "3": demo3_agent_memory,
        "4": demo4_graph,
        "5": demo5_live,
        "6": demo6_rag,
        "a": run_all,
    }
    
    func = demos.get(choice, run_all)
    
    try:
        await func()
    except KeyboardInterrupt:
        print("\n⏹ Canceled")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure SurrealDB is running: docker-compose up -d")


if __name__ == "__main__":
    asyncio.run(main())