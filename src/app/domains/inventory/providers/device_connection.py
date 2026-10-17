"""External providers for GNS3 metadata and network device connections."""

from typing import Any

from netmiko import ConnectHandler

from app.core.config import Settings
from app.domains.inventory.repositories import DeviceConfigRepository
from app.domains.inventory.schemas import DeviceConfig


class DeviceConnectionProvider:
    """Read device configuration from a repository and connect with Netmiko."""

    def __init__(
        self,
        settings: Settings,
        repository: DeviceConfigRepository,
    ) -> None:
        self._settings = settings
        self._repository = repository

    @property
    def gns3_urls(self) -> dict[str, str]:
        base_url = f"http://{self._settings.gns3_ip}:{self._settings.gns3_port}/v2"
        project_url = f"{base_url}/projects/{self._settings.project_id}"
        return {
            "version": f"{base_url}/version",
            "project": project_url,
            "links": f"{project_url}/links",
            "nodes": f"{project_url}/nodes",
        }

    def get_device_config(self, device_identifier: str) -> DeviceConfig | None:
        """Load one connection-ready device from PostgreSQL."""
        return self._repository.get(device_identifier)

    def connect(self, device_identifier: str) -> dict[str, Any]:
        """Open a Netmiko connection and return an explicit success result."""
        device = self.get_device_config(device_identifier)
        if device is None:
            return {
                "success": False,
                "error": (
                    f"Không tìm thấy thiết bị hoặc credential cho "
                    f"'{device_identifier}' trong database"
                ),
            }

        connection_params = device.to_netmiko_params()
        connection_params.update(
            conn_timeout=self._settings.ssh_timeout,
            auth_timeout=self._settings.ssh_auth_timeout,
            global_delay_factor=self._settings.ssh_delay_factor,
        )

        try:
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
