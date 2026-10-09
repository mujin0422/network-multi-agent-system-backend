"""Agent registration and lookup."""

from collections.abc import Iterable

from app.agents.base import BaseAgent


class AgentNotFoundError(LookupError):
    """Raised when routing selects an agent that is not registered."""


class AgentRegistry:
    """Store agent instances behind stable names."""

    def __init__(self, agents: Iterable[BaseAgent] = ()) -> None:
        self._agents: dict[str, BaseAgent] = {}
        for agent in agents:
            self.register(agent)

    def register(self, agent: BaseAgent) -> None:
        self._agents[agent.name] = agent

    def get(self, name: str) -> BaseAgent:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise AgentNotFoundError(f"Unknown agent: {name}") from exc

    def names(self) -> list[str]:
        return list(self._agents)
