#!/usr/bin/env python3
"""
Component: Gaming

Gaming application component.
Based on: https://surrealdb.com/solutions (Gaming use case)
"""

import asyncio
import random
from surrealdb import Surreal


class GamingDB:
    """Gaming database component (agentic NPCs, leaderboards, inventory)."""
    
    def __init__(self, url: str = "ws://localhost:8000/rpc"):
        self.url = url
        self.db = None
    
    async def connect(self):
        self.db = Surreal(self.url)
        await self.db.connect()
        await self.db.use({"namespace": "gaming", "database": "main"})
        await self.db.signin({"username": "root", "password": "root"})
        return self
    
    async def setup_schema(self):
        """Gaming schema."""
        schemas = [
            # Players
            """
            DEFINE TABLE player SCHEMAFULL;
            DEFINE FIELD username ON player TYPE string;
            DEFINE FIELD level ON player TYPE int DEFAULT 1;
            DEFINE FIELD xp ON player TYPE int DEFAULT 0;
            DEFINE FIELD gold ON player TYPE int DEFAULT 100;
            DEFINE FIELD health ON player TYPE int DEFAULT 100;
            DEFINE FIELD max_health ON player TYPE int DEFAULT 100;
            DEFINE FIELD inventory ON player TYPE array<object>;
            DEFINE FIELD location ON player TYPE string;
            DEFINE FIELD status ON player TYPE string DEFAULT 'online';
            """,
            # NPCs with AI
            """
            DEFINE TABLE npc SCHEMAFULL;
            DEFINE FIELD name ON npc TYPE string;
            DEFINE FIELD role ON npc TYPE string; -- merchant, quest_giver, enemy, companion
            DEFINE FIELD dialogue ON npc TYPE array<string>;
            DEFINE FIELD personality ON npc TYPE object;
            DEFINE FIELD health ON npc TYPE int;
            DEFINE FIELD stats ON npc TYPE object;
            DEFINE FIELD memory ON npc TYPE array<object>;
            """,
            # Quests
            """
            DEFINE TABLE quest SCHEMAFULL;
            DEFINE FIELD title ON quest TYPE string;
            DEFINE FIELD description ON quest TYPE string;
            DEFINE FIELD giver ON quest TYPE record(npc);
            DEFINE FIELD goals ON quest TYPE array<object>;
            DEFINE FIELD rewards ON quest TYPE object;
            DEFINE FIELD difficulty ON quest TYPE string; -- easy, medium, hard, epic
            """,
            # Leaderboard
            """
            DEFINE TABLE score SCHEMAFULL;
            DEFINE FIELD player ON score TYPE record(player);
            DEFINE FIELD game ON score TYPE string;
            DEFINE FIELD points ON score TYPE int;
            DEFINE FIELD timestamp ON score TYPE datetime DEFAULT time::now();
            """,
        ]
        
        for schema in schemas:
            await self.db.query(schema)
        print("✅ Gaming schema created")
    
    # ----- NPC with Memory -----
    
    async def create_npc(self, name: str, role: str, dialogue: list, personality: dict):
        """Create AI NPC."""
        result = await self.db.query(
            """CREATE npc SET name=$name, role=$role, dialogue=$dialogue,
            personality=$personality, health=100, memory=[]""",
            {"name": name, "role": role, "dialogue": dialogue, "personality": personality}
        )
        return result[0][0]
    
    async def npc_interact(self, npc_id: str, player_message: str) -> str:
        """NPC responds based on memory and personality."""
        npc = await self.db.query("SELECT * FROM npc WHERE id = $id", {"id": npc_id})
        
        if not npc or not npc[0]:
            return "NPC not found"
        
        npc = npc[0][0]
        personality = npc.get("personality", {})
        
        # Get NPC's memory of player
        memory = await self.db.query(
            """SELECT * FROM context WHERE entity CONTAINS $player""",
            {"player": npc.get("name", "")}
        )
        
        # Generate response based on personality
        responses = npc.get("dialogue", ["Hello, traveler."])
        mood = personality.get("mood", "neutral")
        
        if mood == "friendly":
            response = random.choice([
                f"It's so good to see you again! {random.choice(responses)}",
                f"I've been thinking about you. {random.choice(responses)}"
            ])
        elif mood == "grumpy":
            response = random.choice([
                "What do you want?",
                "Hmmph. " + random.choice(responses)
            ])
        else:
            response = random.choice(responses)
        
        # Store interaction in NPC memory
        await self.db.query(
            """UPDATE npc SET memory += { timestamp: time::now(),
            player_message: $msg, response: $resp } WHERE id = $id""",
            {"id": npc_id, "msg": player_message, "resp": response}
        )
        
        return response
    
    # ----- Player Inventory -----
    
    async def add_item(self, player_id: str, item: dict):
        """Add item to player inventory."""
        result = await self.db.query(
            "UPDATE player SET inventory += $item WHERE id = $id",
            {"id": player_id, "item": item}
        )
        return result[0][0] if result else None
    
    async def use_item(self, player_id: str, item_name: str) -> dict:
        """Use item from inventory."""
        player = await self.db.query("SELECT * FROM player WHERE id = $id", {"id": player_id})
        if not player or not player[0]:
            return {"error": "Player not found"}
        
        # Find item
        inventory = player[0][0].get("inventory", [])
        item = next((i for i in inventory if i.get("name") == item_name), None)
        
        if not item:
            return {"error": f"Item not found: {item_name}"}
        
        # Apply effect
        effects = item.get("effects", {})
        updates = {}
        
        if "health" in effects:
            updates["health"] = min(
                player[0][0].get("max_health", 100),
                player[0][0].get("health", 0) + effects["health"]
            )
        
        if updates:
            await self.db.query(
                "UPDATE player SET health = $health WHERE id = $id",
                {"id": player_id, "health": updates["health"]}
            )
        
        return {"used": item_name, "effects": effects}
    
    # ----- Leaderboard -----
    
    async def submit_score(self, player_id: str, game: str, points: int):
        """Submit player score."""
        result = await self.db.query(
            """CREATE score SET player=$player, game=$game, points=$points""",
            {"player": player_id, "game": game, "points": points}
        )
        return result[0][0]
    
    async def get_leaderboard(self, game: str, limit: int = 10) -> list:
        """Get top scores."""
        result = await self.db.query(
            """SELECT player->{username}, points FROM score WHERE game = $game
            ORDER BY points DESC LIMIT $limit""",
            {"game": game, "limit": limit}
        )
        return result[0] if result else []


async def demo():
    """Gaming demo."""
    db = GamingDB()
    await db.connect()
    await db.setup_schema()
    
    # Create NPC
    npc = await db.create_npc(
        name="Eldrin",
        role="quest_giver",
        dialogue=["Greetings, adventurer!", "The ancient ruins hold many secrets."],
        personality={"mood": "friendly", "trust": 0.5}
    )
    print(f"Created NPC: {npc['name']}")
    
    # Interact
    response = await db.npc_interact(npc["id"], "Hello!")
    print(f"NPC says: {response}")
    
    # Leaderboard
    await db.submit_score("player:hero", "dragon_quest", 1000)
    scores = await db.get_leaderboard("dragon_quest")
    print(f"Top scores: {scores}")


if __name__ == "__main__":
    asyncio.run(demo())