"""FastAPI application entry point and top-level router composition."""

from fastapi import APIRouter, FastAPI

from app.agents.routers import agents_router, chat_router
from app.core.config import get_settings
from app.core.exceptions.handlers import register_error_handlers
from app.domains.conversation.routers import router as conversation_router
from app.domains.execution.routers import (
    operations_router,
    router as execution_router,
)
from app.domains.inventory.routers import (
    brand_router,
    category_router,
    credential_router,
    router as inventory_router,
)
from app.domains.identity.routers import auth_router, role_router, user_router


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.app_debug,
)

register_error_handlers(app)

API_V1_PREFIX = "/api/v1"
v1_router = APIRouter(prefix=API_V1_PREFIX)

v1_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
v1_router.include_router(user_router, prefix="/users", tags=["Users"])
v1_router.include_router(role_router, prefix="/roles", tags=["Roles"])
v1_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
v1_router.include_router(agents_router, prefix="/agents", tags=["Agents"])
v1_router.include_router(brand_router, prefix="/brands", tags=["Brands"])
v1_router.include_router(category_router, prefix="/categories", tags=["Categories"])
v1_router.include_router(
    credential_router,
    prefix="/credentials",
    tags=["Credentials"],
)
v1_router.include_router(
    conversation_router,
    prefix="/conversations",
    tags=["Conversations"],
)
v1_router.include_router(inventory_router, prefix="/devices", tags=["Devices"])
v1_router.include_router(execution_router, prefix="/tasks", tags=["Tasks"])
v1_router.include_router(
    operations_router,
    prefix="/operations",
    tags=["Operations"],
)
app.include_router(v1_router)


@app.get("/health")
async def health_check():
    return {"status": "running"}
