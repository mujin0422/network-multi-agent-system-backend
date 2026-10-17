"""Dependency composition for agent-facing routers."""

from functools import lru_cache

from app.agents.analyst import AnalystAgent
from app.agents.manager import AgentManager
from app.agents.network import NetworkAgent
from app.agents.registry import AgentRegistry


@lru_cache
def _build_agent_manager() -> AgentManager:
    registry = AgentRegistry([NetworkAgent(), AnalystAgent()])
    return AgentManager(registry=registry)


async def get_agent_manager() -> AgentManager:
    return _build_agent_manager()
