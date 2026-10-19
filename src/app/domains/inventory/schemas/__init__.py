"""Public contracts for the Inventory domain."""

from app.domains.inventory.schemas.brand import Brand, BrandCreate, BrandUpdate
from app.domains.inventory.schemas.category import Category
from app.domains.inventory.schemas.credential import (
    Credential,
    CredentialCreate,
    CredentialRecord,
    CredentialUpdate,
)
from app.domains.inventory.schemas.device import (
    Device,
    DeviceCreate,
    DevicePage,
    DeviceUpdate,
)
from app.domains.inventory.schemas.device_connection import DeviceConfig

__all__ = [
    "Brand",
    "BrandCreate",
    "BrandUpdate",
    "Category",
    "Credential",
    "CredentialCreate",
    "CredentialRecord",
    "CredentialUpdate",
    "Device",
    "DeviceConfig",
    "DeviceCreate",
    "DevicePage",
    "DeviceUpdate",
]
