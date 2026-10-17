"""HTTP transport for the Inventory domain."""

from app.domains.inventory.routers.device import router
from app.domains.inventory.routers.network import router as network_router

__all__ = ["network_router", "router"]
