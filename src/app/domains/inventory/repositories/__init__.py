"""Các repository công khai của Inventory domain."""

from app.domains.inventory.repositories.brand import BrandRepository
from app.domains.inventory.repositories.category import CategoryRepository
from app.domains.inventory.repositories.credential import CredentialRepository
from app.domains.inventory.repositories.device import DeviceRepository
from app.domains.inventory.repositories.device_connection import DeviceConfigRepository

__all__ = [
    "BrandRepository",
    "CategoryRepository",
    "CredentialRepository",
    "DeviceRepository",
    "DeviceConfigRepository",
]
