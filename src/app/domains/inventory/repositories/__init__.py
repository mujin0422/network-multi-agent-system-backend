"""Persistence ports and adapters for the Inventory domain."""

from app.domains.inventory.repositories.brand import (
    BrandRepository,
    BrandRepositoryProtocol,
)
from app.domains.inventory.repositories.category import (
    CategoryRepository,
    CategoryRepositoryProtocol,
)
from app.domains.inventory.repositories.credential import (
    CredentialRepository,
    CredentialRepositoryProtocol,
)
from app.domains.inventory.repositories.device import (
    DeviceRepository,
    DeviceRepositoryProtocol,
)
from app.domains.inventory.repositories.device_connection import (
    DeviceConfigRepository,
    DeviceConfigRepositoryProtocol,
)

__all__ = [
    "BrandRepository",
    "BrandRepositoryProtocol",
    "CategoryRepository",
    "CategoryRepositoryProtocol",
    "CredentialRepository",
    "CredentialRepositoryProtocol",
    "DeviceRepository",
    "DeviceRepositoryProtocol",
    "DeviceConfigRepository",
    "DeviceConfigRepositoryProtocol",
]
