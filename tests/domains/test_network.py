"""Device connection tests thuộc Inventory domain."""

from app.core.config import Settings
from app.domains.inventory.providers import DeviceConnectionProvider
from app.domains.inventory.schemas import DeviceConfig


class StubDeviceConfigRepository:
    def get(self, device_identifier: str) -> DeviceConfig | None:
        if device_identifier != "R1":
            return None
        return DeviceConfig(
            hostname="192.0.2.1",
            port=22,
            device_type="cisco_ios",
            username="admin",
            password="secret",
            secret="",
        )


def test_provider_loads_inventory_from_repository() -> None:
    provider = DeviceConnectionProvider(
        Settings(_env_file=None),
        StubDeviceConfigRepository(),
    )

    device = provider.get_device_config("R1")

    assert device is not None
    assert device.username == "admin"
    assert device.to_netmiko_params()["host"] == "192.0.2.1"
