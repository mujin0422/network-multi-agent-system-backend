"""Public API của Network Inventory domain.

Các tầng bên ngoài như FastAPI dependency hoặc agent chỉ nên import những thành
phần được export tại đây. Cách này giúp implementation bên trong domain có thể
thay đổi mà không làm ảnh hưởng tới nơi sử dụng.
"""

from app.domains.inventory.repositories import (
    DeviceConfigRepository,
    InMemoryDeviceRepository,
    PostgresDeviceConfigRepository,
    PostgresDeviceRepository,
)
from app.domains.inventory.providers import DeviceConnectionProvider
from app.domains.inventory.schemas import (
    Brand,
    Category,
    Credential,
    CredentialRecord,
    Device,
    DeviceConfig,
    DeviceCreate,
    DeviceUpdate,
    NetworkStatus,
)
from app.domains.inventory.services import InventoryService, NetworkService

__all__ = [
    "Brand",
    "Category",
    "Credential",
    "CredentialRecord",
    "Device",
    "DeviceConfig",
    "DeviceCreate",
    "DeviceConfigRepository",
    "DeviceConnectionProvider",
    "DeviceUpdate",
    # Service chứa quy tắc nghiệp vụ và là điểm vào chính của domain.
    "InventoryService",
    # Adapter nhẹ dùng cho unit test hoặc chạy thử không cần database.
    "InMemoryDeviceRepository",
    "NetworkService",
    "NetworkStatus",
    "PostgresDeviceConfigRepository",
    # Adapter production đọc và ghi bảng devices trong PostgreSQL.
    "PostgresDeviceRepository",
]
