"""Agent application service."""

from collections.abc import Callable

from app.agents.orchestrator.router import route
from app.agents.registry import AgentRegistry
from app.agents.schemas import ChatResponse


class AgentManager:
    """Route chat messages and invoke registered agents."""

    def __init__(
        self,
        registry: AgentRegistry,
        router: Callable[[str], str] = route,
    ) -> None:
        self._registry = registry
        self._router = router

    async def process(self, message: str) -> ChatResponse:
        agent_name = self._router(message)
        return await self._registry.get(agent_name).execute(message)

    def list_agents(self) -> list[str]:
        return self._registry.names()
