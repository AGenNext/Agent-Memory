"""
Agent Memory Learning Platform

An engaging, interactive learning experience with:
- Live query data from SurrealDB
- Visual canvas for graph traversal
- Interactive testing with fabric.js
- Real-time updates
"""

import asyncio
import uuid
from datetime import datetime

from surrealdb import Surreal
from openai import AsyncOpenAI
from pydantic import BaseModel


# -- Models --

class Course(BaseModel):
    """Learning course."""
    id: str
    title: str
    description: str
    level: str
    lessons: list[str] = []


class LessonProgress(BaseModel):
    """User progress in a lesson."""
    id: str
    user_id: str
    course_id: str
    lesson_id: str
    completed: bool = False
    completed_at: datetime | None = None


class QueryAttempt(BaseModel):
    """Record of a query attempt."""
    id: str
    user_id: str
    query: str
    success: bool
    result: str | None = None
    error: str | None = None
    created: datetime | None = None


class CanvasState(BaseModel):
    """Visual canvas state for graph visualization."""
    id: str
    user_id: str
    nodes: list[dict] = []
    edges: list[dict] = []
    viewport: dict = {"x": 0, "y": 0, "zoom": 1}


# -- Learning Platform --

class LearningPlatform:
    """
    Interactive Learning Platform with SurrealDB.
    
    Features:
    - Course management
    - Lesson progress tracking
    - Query playground with live results
    - Visual graph canvas (fabric.js compatible)
    - Real-time updates
    """
    
    def __init__(self, db: Surreal, llm: AsyncOpenAI):
        self.db = db
        self.llm = llm
    
    # -- Courses --
    
    async def create_course(
        self,
        title: str,
        description: str,
        level: str,
        lessons: list[str],
    ) -> str:
        """Create a new course."""
        cid = f"course:{uuid.uuid4().hex[:8]}"
        
        await self.db.query(
            f"""CREATE {cid} SET
                title = $title,
                description = $description,
                level = $level,
                lessons = $lessons,
                created = time::now();""",
            {
                "title": title,
                "description": description,
                "level": level,
                "lessons": lessons,
            },
        )
        
        return cid
    
    async def get_course(self, course_id: str) -> dict | None:
        """Get course details."""
        result = await self.db.query(
            "SELECT * FROM type::record($id);",
            {"id": course_id},
        )
        
        if result and result[0]:
            return result[0][0] if result[0] else None
        return None
    
    async def list_courses(self) -> list[dict]:
        """List all courses."""
        result = await self.db.query("SELECT * FROM course ORDER BY created DESC;")
        
        if result and result[0]:
            return result[0]
        return []
    
    # -- Progress --
    
    async def start_lesson(
        self,
        user_id: str,
        course_id: str,
        lesson_id: str,
    ) -> str:
        """Track lesson start."""
        pid = f"progress:{uuid.uuid4().hex[:8]}"
        
        await self.db.query(
            f"""CREATE {pid} SET
                user_id = $user_id,
                course_id = $course_id,
                lesson_id = $lesson_id,
                completed = false,
                started = time::now();""",
            {
                "user_id": user_id,
                "course_id": course_id,
                "lesson_id": lesson_id,
            },
        )
        
        return pid
    
    async def complete_lesson(
        self,
        user_id: str,
        course_id: str,
        lesson_id: str,
    ) -> bool:
        """Mark lesson as complete."""
        result = await self.db.query(
            f"""UPDATE progress SET 
                completed = true,
                completed_at = time::now()
            WHERE user_id = $user_id 
            AND course_id = $course_id 
            AND lesson_id = $lesson_id;""",
            {
                "user_id": user_id,
                "course_id": course_id,
                "lesson_id": lesson_id,
            },
        )
        
        return True
    
    async def get_progress(self, user_id: str, course_id: str) -> dict:
        """Get user progress for a course."""
        result = await self.db.query(
            """SELECT * FROM progress 
            WHERE user_id = $user_id AND course_id = $course_id;""",
            {"user_id": user_id, "course_id": course_id},
        )
        
        lessons = result[0] if result and result[0] else []
        
        completed = [l["lesson_id"] for l in lessons if l.get("completed")]
        
        return {
            "completed": completed,
            "total": len(lessons),
            "percentage": len(completed) / max(len(lessons), 1) * 100,
        }
    
    # -- Query Playground --
    
    async def execute_query(
        self,
        user_id: str,
        query: str,
    ) -> dict:
        """
        Execute a SurrealQL query and track the attempt.
        Records success/failure for learning analytics.
        """
        attempt_id = f"attempt:{uuid.uuid4().hex[:8]}"
        
        try:
            # Execute the query
            result = await self.db.query(query)
            
            # Record successful attempt
            await self.db.query(
                f"""CREATE {attempt_id} SET
                    user_id = $user_id,
                    query = $query,
                    success = true,
                    result = $result,
                    created = time::now();""",
                {
                    "user_id": user_id,
                    "query": query,
                    "result": str(result)[:1000],  # Truncate for storage
                },
            )
            
            return {
                "success": True,
                "result": result,
                "attempt_id": attempt_id,
            }
            
        except Exception as e:
            # Record failed attempt
            await self.db.query(
                f"""CREATE {attempt_id} SET
                    user_id = $user_id,
                    query = $query,
                    success = false,
                    error = $error,
                    created = time::now();""",
                {
                    "user_id": user_id,
                    "query": query,
                    "error": str(e),
                },
            )
            
            return {
                "success": False,
                "error": str(e),
                "attempt_id": attempt_id,
            }
    
    async def get_query_history(self, user_id: str) -> list[dict]:
        """Get user's query history."""
        result = await self.db.query(
            """SELECT * FROM attempt 
            WHERE user_id = $user_id 
            ORDER BY created DESC 
            LIMIT 50;""",
            {"user_id": user_id},
        )
        
        return result[0] if result and result[0] else []
    
    # -- Visual Canvas --
    
    async def save_canvas_state(
        self,
        user_id: str,
        nodes: list[dict],
        edges: list[dict],
        viewport: dict = None,
    ) -> str:
        """Save visual canvas state for graph visualization."""
        canvas_id = f"canvas:{uuid.uuid4().hex[:8]}"
        
        await self.db.query(
            f"""CREATE {canvas_id} SET
                user_id = $user_id,
                nodes = $nodes,
                edges = $edges,
                viewport = $viewport,
                updated = time::now();""",
            {
                "user_id": user_id,
                "nodes": nodes,
                "edges": edges,
                "viewport": viewport or {"x": 0, "y": 0, "zoom": 1},
            },
        )
        
        return canvas_id
    
    async def load_canvas_state(self, user_id: str) -> CanvasState | None:
        """Load user's latest canvas state."""
        result = await self.db.query(
            """SELECT * FROM canvas 
            WHERE user_id = $user_id 
            ORDER BY updated DESC 
            LIMIT 1;""",
            {"user_id": user_id},
        )
        
        if result and result[0] and result[0][0]:
            data = result[0][0]
            return CanvasState(
                id=data["id"],
                user_id=data["user_id"],
                nodes=data.get("nodes", []),
                edges=data.get("edges", []),
                viewport=data.get("viewport", {"x": 0, "y": 0, "zoom": 1}),
            )
        
        return None
    
    # -- Graph Visualization Data --
    
    async def get_graph_data(self, record_id: str) -> dict:
        """
        Get graph data for visualization.
        Returns nodes and edges for fabric.js canvas.
        """
        table = record_id.split(":")[0]
        
        # Get the record
        result = await self.db.query(
            "SELECT * FROM type::record($id);",
            {"id": record_id},
        )
        
        if not result or not result[0] or not result[0][0]:
            return {"nodes": [], "edges": []}
        
        record = result[0][0]
        nodes = []
        edges = []
        
        # Add main node
        nodes.append({
            "id": record_id,
            "label": f"{table}:{record.get('name', record.get('title', 'unnamed'))}",
            "type": table,
            "data": record,
        })
        
        # Find related records
        related_queries = {
            "session": "SELECT * FROM entity WHERE session = $id",
            "entity": "SELECT * FROM relationship WHERE from_entity = $id OR to_entity = $id",
            "article": "SELECT * FROM product WHERE <-references<-article = $id",
            "product": "SELECT * FROM article WHERE ->references->product = $id",
        }
        
        if table in related_queries:
            rel_result = await self.db.query(
                related_queries[table],
                {"id": record_id},
            )
            
            if rel_result and rel_result[0]:
                for r in rel_result[0]:
                    rel_id = str(r.get("id", ""))
                    if rel_id:
                        nodes.append({
                            "id": rel_id,
                            "label": f"{rel_id.split(':')[0]}",
                            "type": rel_id.split(":")[0],
                            "data": r,
                        })
                        edges.append({
                            "from": record_id,
                            "to": rel_id,
                            "label": r.get("type", "related"),
                        })
        
        return {"nodes": nodes, "edges": edges}
    
    # -- Live Updates --
    
    async def subscribe_to_course(self, course_id: str):
        """Subscribe to course updates (live query)."""
        await self.db.query(
            f"LIVE SELECT * FROM progress WHERE course_id = $course_id;",
            {"course_id": course_id},
        )
        
        async for change in self.db.listen():
            yield change
    
    # -- Analytics --
    
    async def get_learning_stats(self, user_id: str) -> dict:
        """Get user's learning statistics."""
        # Query attempts
        attempts = await self.db.query(
            """SELECT 
                count() as total,
                math::sum(IF success THEN 1 ELSE 0 END) as successful
            FROM attempt 
            WHERE user_id = $user_id 
            GROUP ALL;""",
            {"user_id": user_id},
        )
        
        # Progress
        progress = await self.db.query(
            """SELECT count() as completed 
            FROM progress 
            WHERE user_id = $user_id AND completed = true;""",
            {"user_id": user_id},
        )
        
        attempts_data = attempts[0][0] if attempts and attempts[0] else {}
        progress_data = progress[0][0] if progress and progress[0] else {}
        
        return {
            "total_queries": attempts_data.get("total", 0),
            "successful_queries": attempts_data.get("successful", 0),
            "success_rate": attempts_data.get("successful", 0) / max(attempts_data.get("total", 1), 1) * 100,
            "lessons_completed": progress_data.get("completed", 0),
        }


# -- Default Courses --

DEFAULT_COURSES = [
    {
        "title": "Querying Fundamentals",
        "description": "Learn SurrealQL basics: CREATE, SELECT, UPDATE, DELETE",
        "level": "beginner",
        "lessons": [
            "Introduction to SurrealQL",
            "CREATE - Inserting Data",
            "SELECT - Reading Data",
            "UPDATE - Modifying Data",
            "DELETE - Removing Data",
        ],
    },
    {
        "title": "Advanced Querying",
        "description": "LIVE queries, full-text search, and vector similarity",
        "level": "intermediate",
        "lessons": [
            "LIVE Queries - Real-time",
            "Full-Text Search",
            "Vector Similarity",
            "Hybrid Search",
        ],
    },
    {
        "title": "Data Models",
        "description": "Documents, graphs, vectors, and time-series",
        "level": "beginner",
        "lessons": [
            "Document Model",
            "Graph Model",
            "Vector Model",
            "Time-Series",
        ],
    },
    {
        "title": "Graph Relationships",
        "description": "Entity relationships and traversal",
        "level": "intermediate",
        "lessons": [
            "Basic Relationships",
            "Traversal",
            "Path Operations",
        ],
    },
]


async def initialize_courses(platform: LearningPlatform) -> int:
    """Initialize default courses."""
    count = 0
    for course in DEFAULT_COURSES:
        await platform.create_course(
            title=course["title"],
            description=course["description"],
            level=course["level"],
            lessons=course["lessons"],
        )
        count += 1
    return count


# -- Demo --

async def demo():
    """Demo the learning platform."""
    from agent_memory import AgentMemory, Config
    
    config = Config()
    memory = AgentMemory(config)
    await memory.connect()
    
    llm = AsyncOpenAI()
    
    platform = LearningPlatform(memory._db, llm)
    
    # Initialize courses
    print("=== Initializing Courses ===")
    count = await initialize_courses(platform)
    print(f"Created {count} courses")
    
    # List courses
    print("\n=== Available Courses ===")
    courses = await platform.list_courses()
    for c in courses:
        print(f"- {c['title']} ({c['level']})")
    
    # Execute query
    print("\n=== Query Playground ===")
    result = await platform.execute_query(
        user_id="user:demo",
        query="SELECT * FROM course LIMIT 5;",
    )
    print(f"Success: {result['success']}")
    
    # Save canvas state
    print("\n=== Canvas State ===")
    canvas_id = await platform.save_canvas_state(
        user_id="user:demo",
        nodes=[
            {"id": "user:alice", "label": "Alice"},
            {"id": "session:1", "label": "Session"},
        ],
        edges=[
            {"from": "user:alice", "to": "session:1", "label": "created"},
        ],
    )
    print(f"Canvas saved: {canvas_id}")
    
    # Get learning stats
    print("\n=== Learning Stats ===")
    stats = await platform.get_learning_stats("user:demo")
    print(f"Stats: {stats}")
    
    await memory.close()


if __name__ == "__main__":
    asyncio.run(demo())