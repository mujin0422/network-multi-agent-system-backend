from app.domains.identity.routers.auth import router as auth_router
from app.domains.identity.routers.role import router as role_router
from app.domains.identity.routers.user import router as user_router

__all__ = ["auth_router", "role_router", "user_router"]
