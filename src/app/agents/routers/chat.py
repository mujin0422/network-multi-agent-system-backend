"""Chat transport endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.agents.dependencies import get_agent_manager
from app.agents.manager import AgentManager
from app.agents.schemas import ChatRequest, ChatResponse


router = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    manager: Annotated[AgentManager, Depends(get_agent_manager)],
) -> ChatResponse:
    """Process one stateless chat turn through the selected agent."""
    return await manager.process(request.message)
