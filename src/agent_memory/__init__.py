"""
Agent Memory SDK - Core module.

Build AI agents with persistent memory using knowledge graphs and vectors on SurrealDB.
"""

from .client import AgentMemory
from .config import Config
from .types import Session, Message, Entity, Relationship
from .orchestrator import Orchestrator
from .chat import ChatStream

__version__ = "0.1.0"

# Browser export (use in browser/deno)
# from .browser import BrowserMemory

__all__ = [
    "AgentMemory",
    "Config",
    "Session", 
    "Message",
    "Entity",
    "Relationship",
    "Orchestrator",
    "ChatStream",
]