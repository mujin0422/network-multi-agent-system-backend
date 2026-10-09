"""Network domain transport endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_network_service
from app.domains.network.schemas import NetworkStatus
from app.domains.network.service import NetworkService


router = APIRouter()


@router.get("/", response_model=NetworkStatus)
async def network_status(
    service: Annotated[NetworkService, Depends(get_network_service)],
) -> NetworkStatus:
    """Return the network domain readiness status."""
    return service.status()
