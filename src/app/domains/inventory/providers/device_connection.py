"""External providers for GNS3 metadata and network device connections."""

from typing import Any

from netmiko import ConnectHandler

from app.core.config import Settings
from app.domains.inventory.repositories import DeviceConfigRepositoryProtocol
from app.domains.inventory.schemas import DeviceConfig


class DeviceConnectionProvider:
    """Read device configuration from a repository and connect with Netmiko."""

    def __init__(
        self,
        settings: Settings,
        repository: DeviceConfigRepositoryProtocol,
    ) -> None:
        self._settings = settings
        self._repository = repository

    def get_device_config(self, device_identifier: str) -> DeviceConfig | None:
        """Load one connection-ready device from PostgreSQL."""
        return self._repository.get(device_identifier)

    def prepare_device(self, device_identifier: str) -> DeviceConfig:
        """Lấy config kết nối đã giải mã từ database."""

        device = self.get_device_config(device_identifier)
        if device is None:
            raise ConnectionError(
                f"Không tìm thấy thiết bị hoặc credential cho '{device_identifier}' "
                "trong database"
            )
        return device

    def connect(self, device_identifier: str) -> dict[str, Any]:
        """Open a Netmiko connection and return an explicit success result."""
        try:
            device = self.prepare_device(device_identifier)
            connection_params = device.to_netmiko_params()
            connection_params.update(
                conn_timeout=self._settings.ssh_timeout,
                auth_timeout=self._settings.ssh_auth_timeout,
                global_delay_factor=self._settings.ssh_delay_factor,
            )
            connection = ConnectHandler(**connection_params)
            if device.secret and not connection.check_enable_mode():
                connection.enable()
            return {
                "success": True,
                "device": device_identifier,
                "connection": connection,
            }
        except Exception as exc:
            return {
                "success": False,
                "device": device_identifier,
                "error": f"Kết nối thất bại: {exc}",
            }
