"""HTTP routes cung cấp Network Inventory cho frontend."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from app.domains.identity.routers.dependencies import require_permission

from app.domains.inventory.schemas import Device, DeviceCreate, DeviceUpdate
from app.domains.inventory.routers.dependencies import get_inventory_service
from app.domains.inventory.services import InventoryService


router = APIRouter()


@router.post("/", response_model=Device, status_code=status.HTTP_201_CREATED)
async def create_device(
    payload: DeviceCreate,
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    _user: Annotated[object, Depends(require_permission("Device Management", "Add"))],
) -> Device:
    return service.create_device(payload)


@router.get("/", response_model=list[Device])
async def list_devices(
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    _user: Annotated[object, Depends(require_permission("Device Management", "View"))],
) -> list[Device]:
    return service.list_devices()


@router.get("/{device_id}", response_model=Device)
async def get_device(
    device_id: str,
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    _user: Annotated[object, Depends(require_permission("Device Management", "View"))],
) -> Device:
    return service.get_device(device_id)


@router.patch("/{device_id}", response_model=Device)
async def update_device(
    device_id: str,
    payload: DeviceUpdate,
    service: Annotated[InventoryService, Depends(get_inventory_service)],
    _user: Annotated[object, Depends(require_permission("Device Management", "Edit"))],
) -> Device:
    return service.update_device(device_id, payload)
