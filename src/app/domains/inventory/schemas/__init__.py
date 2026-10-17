"""Public contracts for the Inventory domain."""

from app.domains.inventory.schemas.brand import Brand
from app.domains.inventory.schemas.category import Category
from app.domains.inventory.schemas.credential import Credential, CredentialRecord
from app.domains.inventory.schemas.device import Device, DeviceCreate, DeviceUpdate
from app.domains.inventory.schemas.device_connection import DeviceConfig
from app.domains.inventory.schemas.network_status import NetworkStatus

__all__ = [
    "Brand",
    "Category",
    "Credential",
    "CredentialRecord",
    "Device",
    "DeviceConfig",
    "DeviceCreate",
    "DeviceUpdate",
    "NetworkStatus",
]
