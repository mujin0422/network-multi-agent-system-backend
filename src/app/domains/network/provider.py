"""External providers for GNS3 metadata and network device connections."""

from pathlib import Path
from typing import Any

import yaml
from netmiko import ConnectHandler

from app.core.config import Settings
from app.domains.network.schemas import DeviceConfig


class DeviceConnectionProvider:
    """Read device inventory and establish Netmiko connections."""

    def __init__(
        self,
        settings: Settings,
        inventory_path: Path = Path("config/devices.yaml"),
    ) -> None:
        self._settings = settings
        self._inventory_path = inventory_path

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
        """Load and validate one device from the YAML inventory."""
        if not self._inventory_path.exists():
            return None

        with self._inventory_path.open(encoding="utf-8") as inventory_file:
            inventory = yaml.safe_load(inventory_file) or {}

        raw_config = inventory.get(device_identifier)
        if raw_config is None:
            return None

        defaults = {
            "hostname": self._settings.default_device_hostname,
            "port": self._settings.default_device_port,
            "device_type": self._settings.default_device_type,
            "username": self._settings.default_device_username,
            "password": self._settings.default_device_password,
        }
        return DeviceConfig.model_validate(defaults | raw_config)

    def connect(self, device_identifier: str) -> dict[str, Any]:
        """Open a Netmiko connection and return an explicit success result."""
        device = self.get_device_config(device_identifier)
        if device is None:
            return {
                "success": False,
                "error": f"Không tìm thấy cấu hình cho '{device_identifier}' trong devices.yaml",
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
