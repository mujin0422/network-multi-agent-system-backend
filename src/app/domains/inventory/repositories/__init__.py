"""Persistence ports and adapters for the Inventory domain."""

from app.domains.inventory.repositories.brand import (
    BrandRepository,
    PostgresBrandRepository,
)
from app.domains.inventory.repositories.category import (
    CategoryRepository,
    PostgresCategoryRepository,
)
from app.domains.inventory.repositories.credential import (
    CredentialRepository,
    PostgresCredentialRepository,
)
from app.domains.inventory.repositories.device import (
    DeviceRepository,
    PostgresDeviceRepository,
)
from app.domains.inventory.repositories.device_connection import (
    DeviceConfigRepository,
    PostgresDeviceConfigRepository,
)

__all__ = [
    "BrandRepository",
    "CategoryRepository",
    "CredentialRepository",
    "DeviceRepository",
    "DeviceConfigRepository",
    "PostgresBrandRepository",
    "PostgresCategoryRepository",
    "PostgresCredentialRepository",
    "PostgresDeviceConfigRepository",
    "PostgresDeviceRepository",
]
