"""Built-in analyst agent."""

from app.agents.base import BaseAgent
from app.agents.schemas import ChatResponse


class AnalystAgent(BaseAgent):
    name = "analyst_agent"

    async def execute(self, message: str) -> ChatResponse:
        return ChatResponse(
            agent=self.name,
            response=f"Analyst processed: {message}",
        )
