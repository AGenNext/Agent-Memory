"""
SurrealDB Orchestrator Agent - Coordinates multiple agents and tools.

The orchestrator manages a team of specialized agents, delegates tasks,
and coordinates their work using SurrealDB for memory and state.
"""

import uuid
import asyncio
from typing import Any, Callable
from datetime import datetime

from openai import AsyncOpenAI
from surrealdb import Surreal
from pydantic import BaseModel


# -- Agent Types --

class AgentSpec(BaseModel):
    """Specification for a team agent."""
    id: str
    name: str
    description: str
    tools: list[str]
    prompt: str
    model: str = "gpt-4o-mini"
    status: str = "idle"


class Task(BaseModel):
    """A task to be executed by an agent."""
    id: str
    agent_id: str
    input: str
    status: str = "pending"
    result: str | None = None
    error: str | None = None
    created: datetime | None = None
    started: datetime | None = None
    completed: datetime | None = None


class Delegation(BaseModel):
    """A delegation from orchestrator to agent."""
    id: str
    task_id: str
    from_agent: str
    to_agent: str
    status: str = "pending"
    created: datetime | None = None


class Orchestrator:
    """
    Orchestrator Agent - Manages a team of specialized agents.
    
    Example:
        orch = Orchestrator(db, llm)
        
        # Register team agents
        await orch.register_agent(
            name="researcher",
            description="Web search and info gathering",
            tools=["search", "crawl"],
            prompt="You are a research agent. Find information."
        )
        
        # Delegate a task
        task_id = await orch.delegate(
            to_agent="researcher",
            input="Find info on SurrealDB extensions"
        )
        
        # Get result
        result = await orch.get_result(task_id)
    """
    
    def __init__(self, db: Surreal, llm: AsyncOpenAI):
        self.db = db
        self.llm = llm
        self._agents: dict[str, AgentSpec] = {}
        self._tools: dict[str, Callable] = {}
    
    # -- Agent Registration --
    
    async def register_agent(
        self,
        name: str,
        description: str,
        tools: list[str],
        prompt: str,
        model: str = "gpt-4o-mini",
    ) -> str:
        """Register a new agent in the team."""
        aid = f"agent:{name}"
        
        # Store in DB
        await self.db.query(
            f"""CREATE {aid} SET
                name = $name,
                description = $description,
                tools = $tools,
                prompt = $prompt,
                model = $model,
                status = 'idle',
                created = time::now();""",
            {
                "name": name,
                "description": description,
                "tools": tools,
                "prompt": prompt,
                "model": model,
            },
        )
        
        # Cache locally
        self._agents[aid] = AgentSpec(
            id=aid,
            name=name,
            description=description,
            tools=tools,
            prompt=prompt,
            model=model,
        )
        
        return aid
    
    async def list_agents(self) -> list[AgentSpec]:
        """List all registered agents."""
        result = await self.db.query("SELECT * FROM agent")
        rows = self._rows(result)
        return [AgentSpec(**r) for r in rows]
    
    async def get_agent(self, agent_id: str) -> AgentSpec | None:
        """Get an agent by ID."""
        result = await self.db.query(
            "SELECT * FROM type::record($id);",
            {"id": agent_id},
        )
        rows = self._rows(result)
        return AgentSpec(**rows[0]) if rows else None
    
    # -- Tool Registration --
    
    def register_tool(self, name: str, func: Callable):
        """Register a tool that agents can use."""
        self._tools[name] = func
    
    async def call_tool(self, name: str, **kwargs) -> Any:
        """Call a registered tool."""
        if name not in self._tools:
            return {"error": f"Unknown tool: {name}"}
        
        func = self._tools[name]
        
        # Execute tool
        if asyncio.iscoroutinefunction(func):
            return await func(**kwargs)
        return func(**kwargs)
    
    # -- Task Delegation --
    
    async def delegate(
        self,
        to_agent: str,
        input: str,
        context: dict | None = None,
    ) -> str:
        """Delegate a task to an agent."""
        tid = f"task:{uuid.uuid4().hex[:8]}"
        
        # Get agent spec
        agent = await self.get_agent(to_agent)
        if not agent:
            raise ValueError(f"Unknown agent: {to_agent}")
        
        # Build prompt with context
        full_prompt = f"{agent.prompt}\n\nTask: {input}"
        if context:
            full_prompt += f"\n\nContext: {context}"
        
        # Execute via LLM
        response = await self.llm.chat.completions.create(
            model=agent.model,
            messages=[
                {"role": "system", "content": full_prompt},
                {"role": "user", "content": input},
            ],
        )
        
        result = response.choices[0].message.content
        
        # Store task result
        await self.db.query(
            f"""CREATE {tid} SET
                agent_id = $agent_id,
                input = $input,
                result = $result,
                status = 'completed',
                created = time::now(),
                completed = time::now();""",
            {"agent_id": to_agent, "input": input, "result": result},
        )
        
        return tid
    
    async def get_result(self, task_id: str) -> str | None:
        """Get the result of a task."""
        result = await self.db.query(
            "SELECT result FROM type::record($id);",
            {"id": task_id},
        )
        rows = self._rows(result)
        return rows[0].get("result") if rows else None
    
    # -- Multi-Agent Coordination --
    
    async def coordinate(
        self,
        task: str,
        agent_sequence: list[str],
    ) -> dict[str, str]:
        """
        Coordinate multiple agents in sequence.
        
        Each agent's output becomes input for the next.
        """
        results = {}
        current_input = task
        
        for i, agent_id in enumerate(agent_sequence):
            task_id = await self.delegate(agent_id, current_input)
            result = await self.get_result(task_id)
            
            results[agent_id] = result
            current_input = result
        
        return results
    
    async def parallel_execute(
        self,
        task: str,
        agent_ids: list[str],
    ) -> dict[str, str]:
        """Execute same task with multiple agents in parallel."""
        results = {}
        
        # Create all delegations
        task_ids = []
        for agent_id in agent_ids:
            tid = await self.delegate(agent_id, task)
            task_ids.append((agent_id, tid))
        
        # Wait for all results
        for agent_id, task_id in task_ids:
            results[agent_id] = await self.get_result(task_id)
        
        return results
    
    # -- Agent Selection --
    
    async def select_agent(self, task: str) -> str | None:
        """
        Automatically select the best agent for a task.
        
        Uses LLM to analyze the task and pick the right agent.
        """
        agents = await self.list_agents()
        
        if not agents:
            return None
        
        # Build agent descriptions
        agent_list = "\n".join([
            f"- {a.name}: {a.description}"
            for a in agents
        ])
        
        response = await self.llm.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"Select the best agent for this task. Return just the agent name.\n\nAvailable agents:\n{agent_list}"
                },
                {"role": "user", "content": task}
            ],
        )
        
        # Parse response
        selected = response.choices[0].message.content.strip()
        
        # Find matching agent
        for agent in agents:
            if agent.name.lower() in selected.lower():
                return agent.id
        
        return agents[0].id
    
    # -- Team Chat --
    
    async def team_chat(
        self,
        message: str,
        include_agents: list[str] | None = None,
    ) -> dict[str, str]:
        """
        Send a message to multiple agents and get their responses.
        """
        agents = await self.list_agents()
        
        if include_agents:
            agents = [a for a in agents if a.id in include_agents]
        
        # Parallel execution
        return await self.parallel_execute(message, [a.id for a in agents])
    
    # -- State Management --
    
    async def get_team_state(self) -> dict:
        """Get current state of all agents."""
        agents = await self.list_agents()
        
        return {
            "total_agents": len(agents),
            "agents": [
                {
                    "id": a.id,
                    "name": a.name,
                    "status": a.status,
                }
                for a in agents
            ]
        }
    
    async def update_agent_status(
        self,
        agent_id: str,
        status: str,
    ):
        """Update an agent's status."""
        await self.db.query(
            "UPDATE type::record($id) SET status = $status;",
            {"id": agent_id, "status": status},
        )
    
    # -- Helpers --
    
    def _rows(self, result) -> list:
        if not result:
            return []
        first = result[0]
        if isinstance(first, dict):
            return result
        if isinstance(first, list):
            return first
        return []


# -- Demo --

async def demo():
    """Demo the orchestrator."""
    from agent_memory import AgentMemory, Config
    
    config = Config()
    memory = AgentMemory(config)
    await memory.connect()
    
    llm = AsyncOpenAI()
    
    orch = Orchestrator(memory._db, llm)
    
    # Register team agents
    print("=== Registering Team Agents ===")
    
    await orch.register_agent(
        name="researcher",
        description="Web research and information gathering",
        tools=["search", "crawl"],
        prompt="You are a research agent. Find accurate information."
    )
    
    await orch.register_agent(
        name="coder",
        description="Code generation and debugging",
        tools=["write_code", "run_tests"],
        prompt="You are a coding agent. Write clean, working code."
    )
    
    await orch.register_agent(
        name="analyst",
        description="Data analysis and insights",
        tools=["analyze", "visualize"],
        prompt="You are an analysis agent. Provide data insights."
    )
    
    # List agents
    agents = await orch.list_agents()
    print(f"Team: {[a.name for a in agents]}")
    
    # Auto-select agent
    print("\n=== Agent Selection ===")
    selected = await orch.select_agent("Find info on SurrealDB extensions")
    print(f"Selected: {selected}")
    
    # Delegate task
    print("\n=== Delegating Task ===")
    task_id = await orch.delegate(selected, "What is hybrid search?")
    result = await orch.get_result(task_id)
    print(f"Result: {result[:200]}...")
    
    # Team chat
    print("\n=== Team Chat ===")
    responses = await orch.team_chat("Explain agent memory")
    for agent_id, response in responses.items():
        print(f"{agent_id}: {response[:100]}...")
    
    await memory.close()


if __name__ == "__main__":
    asyncio.run(demo())