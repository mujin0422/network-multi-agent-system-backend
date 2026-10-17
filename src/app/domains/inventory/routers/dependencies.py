"""Dependency composition for Inventory HTTP routes."""

from functools import lru_cache

from app.core.config import get_settings
from app.domains.inventory import (
    BrandService,
    CategoryService,
    CredentialService,
    DeviceConnectionProvider,
    DeviceService,
    NetworkService,
    PostgresBrandRepository,
    PostgresCategoryRepository,
    PostgresCredentialRepository,
    PostgresDeviceConfigRepository,
    PostgresDeviceRepository,
)


@lru_cache
def _build_brand_service() -> BrandService:
    settings = get_settings()
    return BrandService(PostgresBrandRepository(settings.database_url))


async def get_brand_service() -> BrandService:
    return _build_brand_service()


@lru_cache
def _build_category_service() -> CategoryService:
    settings = get_settings()
    return CategoryService(PostgresCategoryRepository(settings.database_url))


async def get_category_service() -> CategoryService:
    return _build_category_service()


@lru_cache
def _build_credential_service() -> CredentialService:
    settings = get_settings()
    repository = PostgresCredentialRepository(
        database_url=settings.database_url,
        encryption_key=settings.device_credential_encryption_key,
    )
    return CredentialService(repository)


async def get_credential_service() -> CredentialService:
    return _build_credential_service()


@lru_cache
def _build_device_service() -> DeviceService:
    settings = get_settings()
    return DeviceService(PostgresDeviceRepository(settings.database_url))


async def get_device_service() -> DeviceService:
    return _build_device_service()


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
