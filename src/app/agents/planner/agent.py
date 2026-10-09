"""Built-in network agent."""

from app.agents.base import BaseAgent
from app.agents.schemas import ChatResponse


class NetworkAgent(BaseAgent):
    name = "network_agent"

    async def execute(self, message: str) -> ChatResponse:
        return ChatResponse(
            agent=self.name,
            response=f"Network agent handled: {message}",
        )
