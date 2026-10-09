"""Contracts implemented by conversational agents."""

from abc import ABC, abstractmethod

from app.agents.schemas import ChatResponse


class BaseAgent(ABC):
    """Common interface for every registered agent."""

    name: str

    @abstractmethod
    async def execute(self, message: str) -> ChatResponse:
        """Process a message and return a serializable response."""
