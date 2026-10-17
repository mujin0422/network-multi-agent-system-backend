"""HTTP transport for the Inventory domain."""

from app.domains.inventory.routers.brand import router as brand_router
from app.domains.inventory.routers.category import router as category_router
from app.domains.inventory.routers.credential import router as credential_router
from app.domains.inventory.routers.device import router

__all__ = ["brand_router", "category_router", "credential_router", "router"]
