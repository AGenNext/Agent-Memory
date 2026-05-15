"""
Load schema, data, and embeddings into SurrealDB.

This script:
1. Connects to SurrealDB
2. Executes the schema definitions (01-schema.surql)
3. Loads sample data (02-ingest.surql)
4. Generates embeddings for articles
"""

import os
import asyncio

from openai import AsyncOpenAI
from surrealdb import Surreal


async def load_schema(db: Surreal):
    """Load schema definitions from 01-schema.surql."""
    schema_path = os.path.join(os.path.dirname(__file__), "surql", "01-schema.surql")
    with open(schema_path) as f:
        schema = f.read()
    
    # Split by semicolons and execute each statement
    statements = [s.strip() for s in schema.split(";") if s.strip()]
    
    for stmt in statements:
        if stmt:
            try:
                await db.query(stmt)
            except Exception as e:
                print(f"Schema statement error: {e}")
    print("Schema loaded successfully")


async def load_data(db: Surreal):
    """Load sample data from 02-ingest.surql."""
    data_path = os.path.join(os.path.dirname(__file__), "surql", "02-ingest.surql")
    with open(data_path) as f:
        data = f.read()
    
    statements = [s.strip() for s in data.split(";") if s.strip()]
    
    for stmt in statements:
        if stmt:
            try:
                await db.query(stmt)
            except Exception as e:
                print(f"Data statement error: {e}")
    print("Data loaded successfully")


async def generate_embeddings(db: Surreal, llm: AsyncOpenAI):
    """Generate embeddings for all articles."""
    EMBED_MODEL = "text-embedding-3-small"
    
    # Fetch all articles
    articles = await db.query("SELECT * FROM article")
    
    for article in articles:
        content = f"{article['title']} {article['content']}"
        
        # Generate embedding
        resp = await llm.embeddings.create(model=EMBED_MODEL, input=content)
        embedding = resp.data[0].embedding
        
        # Update article with embedding
        article_id = str(article["id"])
        await db.query(
            f"UPDATE {article_id} SET embedding = $emb;",
            {"emb": embedding}
        )
        print(f"Generated embedding for {article_id}")
    
    print("Embeddings generated successfully")


async def main():
    # Connect to SurrealDB
    db = Surreal("ws://localhost:8000/rpc")
    await db.signin({"username": "root", "password": "root"})
    await db.use("demo", "support")
    
    # Initialize OpenAI client
    llm = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    print("Loading schema...")
    await load_schema(db)
    
    print("Loading data...")
    await load_data(db)
    
    print("Generating embeddings...")
    await generate_embeddings(db, llm)
    
    print("\\n=== Load Complete ===")
    print("Run 'uv run agent.py' to start the agent")


if __name__ == "__main__":
    asyncio.run(main())