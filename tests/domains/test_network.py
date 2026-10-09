"""Network domain unit tests."""

from pathlib import Path

from app.core.config import Settings
from app.domains.network.provider import DeviceConnectionProvider


def test_provider_loads_inventory_with_settings_defaults(tmp_path: Path) -> None:
    inventory = tmp_path / "devices.yaml"
    inventory.write_text(
        "R1:\n  hostname: 192.0.2.1\n  port: 22\n  device_type: cisco_ios\n",
        encoding="utf-8",
    )
    settings = Settings(
        _env_file=None,
        default_device_username="admin",
        default_device_password="secret",
    )
    provider = DeviceConnectionProvider(settings, inventory)

    device = provider.get_device_config("R1")

    assert device is not None
    assert device.username == "admin"
    assert device.to_netmiko_params()["host"] == "192.0.2.1"
