"""Network use cases."""

from typing import Any

from app.domains.inventory.providers import DeviceConnectionProvider
from app.domains.inventory.schemas import DeviceConfig


class NetworkService:
    """Coordinate network inventory and connection operations."""

    def __init__(self, provider: DeviceConnectionProvider) -> None:
        """Khởi tạo NetworkService cùng các phụ thuộc cần thiết."""
        self._provider = provider

    # =============================================================================
    # Network — tra cứu, chuẩn bị và kết nối thiết bị
    # =============================================================================

    def get_device(self, device_identifier: str) -> DeviceConfig | None:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_device."""
        return self._provider.get_device_config(device_identifier)

    def prepare_device(self, device_identifier: str) -> DeviceConfig:
        """Chuẩn bị kết nối thiết bị theo nghiệp vụ của phương thức prepare_device."""
        return self._provider.prepare_device(device_identifier)

    def connect(self, device_identifier: str) -> dict[str, Any]:
        """Chuẩn bị kết nối thiết bị theo nghiệp vụ của phương thức connect."""
        return self._provider.connect(device_identifier)
