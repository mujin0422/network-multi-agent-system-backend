"""Device connectivity endpoints owned by the Inventory domain."""

from typing import Annotated

from fastapi import APIRouter, Depends
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User

from app.domains.inventory.routers.dependencies import get_network_service
from app.domains.inventory.schemas import NetworkStatus
from app.domains.inventory.services import NetworkService


router = APIRouter()


@router.get("/", response_model=NetworkStatus)
async def network_status(
    service: Annotated[NetworkService, Depends(get_network_service)],
    _user: Annotated[User, Depends(require_permission("Dashboard", "View"))],
) -> NetworkStatus:
    """Return the network domain readiness status."""
    return service.status()
