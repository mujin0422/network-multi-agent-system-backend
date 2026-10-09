"""Public agent discovery endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.agents.manager import AgentManager
from app.agents.schemas import AgentListResponse
from app.api.dependencies import get_agent_manager


router = APIRouter()


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    manager: Annotated[AgentManager, Depends(get_agent_manager)],
) -> AgentListResponse:
    """Return the stable names of all registered agents."""
    return AgentListResponse(agents=manager.list_agents())
