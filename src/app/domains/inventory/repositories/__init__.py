"""Persistence ports and adapters for the Inventory domain."""

from app.domains.inventory.repositories.device import (
    DeviceRepository,
    InMemoryDeviceRepository,
    PostgresDeviceRepository,
)
from app.domains.inventory.repositories.device_connection import (
    DeviceConfigRepository,
    PostgresDeviceConfigRepository,
)

__all__ = [
    "DeviceRepository",
    "DeviceConfigRepository",
    "InMemoryDeviceRepository",
    "PostgresDeviceConfigRepository",
    "PostgresDeviceRepository",
]
