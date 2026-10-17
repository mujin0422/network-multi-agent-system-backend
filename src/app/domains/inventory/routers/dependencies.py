"""Dependency composition for Inventory HTTP routes."""

from functools import lru_cache

from app.core.config import get_settings
from app.domains.inventory import (
    DeviceConnectionProvider,
    InMemoryDeviceRepository,
    InventoryService,
    NetworkService,
    PostgresDeviceConfigRepository,
    PostgresDeviceRepository,
)


@lru_cache
def _build_inventory_service() -> InventoryService:
    settings = get_settings()
    if settings.inventory_repository_backend == "postgres":
        return InventoryService(PostgresDeviceRepository(settings.database_url))
    return InventoryService(InMemoryDeviceRepository())


async def get_inventory_service() -> InventoryService:
    return _build_inventory_service()


@lru_cache
def _build_network_service() -> NetworkService:
    settings = get_settings()
    repository = PostgresDeviceConfigRepository(
        database_url=settings.database_url,
        encryption_key=settings.device_credential_encryption_key,
    )
    provider = DeviceConnectionProvider(settings=settings, repository=repository)
    return NetworkService(provider=provider)


async def get_network_service() -> NetworkService:
    return _build_network_service()
