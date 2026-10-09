"""Top-level API router."""

from fastapi import APIRouter

from app.api.routes import agents, chat, network


api_router = APIRouter()
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(agents.router, prefix="/agents", tags=["Agents"])
api_router.include_router(network.router, prefix="/network", tags=["Network"])
