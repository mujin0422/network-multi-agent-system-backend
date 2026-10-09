"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import agents, chat, conversations, devices, network, tasks


api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(network.router, prefix="/network", tags=["Network"])
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["Conversations"],
)
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(
    tasks.operations_router,
    prefix="/operations",
    tags=["Operations"],
)
api_router.include_router(
    tasks.change_sets_router,
    prefix="/change-sets",
    tags=["Change Sets"],
)
