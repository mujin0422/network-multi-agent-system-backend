"""External device providers owned by the Inventory domain."""

from app.domains.inventory.providers.device_connection import (
    DeviceConnectionProvider,
)
from app.domains.inventory.providers.gns3 import GNS3Provider

__all__ = ["DeviceConnectionProvider", "GNS3Provider"]
