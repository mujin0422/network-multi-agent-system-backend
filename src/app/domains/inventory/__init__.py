"""Public API của Network Inventory domain.

Các tầng bên ngoài như FastAPI dependency hoặc agent chỉ nên import những thành
phần được export tại đây. Cách này giúp implementation bên trong domain có thể
thay đổi mà không làm ảnh hưởng tới nơi sử dụng.
"""

from app.domains.inventory.repositories import (
    BrandRepository,
    CategoryRepository,
    CredentialRepository,
    DeviceConfigRepository,
    DeviceRepository,
)
from app.domains.inventory.providers import DeviceConnectionProvider, GNS3Provider
from app.domains.inventory.schemas import (
    Brand,
    BrandCreate,
    BrandUpdate,
    Category,
    Credential,
    CredentialCreate,
    CredentialRecord,
    CredentialUpdate,
    Device,
    DeviceConfig,
    DeviceCreate,
    DeviceUpdate,
)
from app.domains.inventory.services import (
    BrandService,
    CategoryService,
    CredentialService,
    DeviceService,
    NetworkService,
)

__all__ = [
    "Brand",
    "BrandCreate",
    "BrandRepository",
    "BrandService",
    "BrandUpdate",
    "Category",
    "CategoryRepository",
    "CategoryService",
    "Credential",
    "CredentialCreate",
    "CredentialRepository",
    "CredentialRecord",
    "CredentialService",
    "CredentialUpdate",
    "Device",
    "DeviceConfig",
    "DeviceCreate",
    "DeviceConfigRepository",
    "DeviceConnectionProvider",
    "GNS3Provider",
    "DeviceRepository",
    "DeviceUpdate",
    "DeviceService",
    "NetworkService",
]
