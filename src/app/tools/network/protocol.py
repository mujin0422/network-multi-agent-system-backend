"""Contract để Network Agent không phụ thuộc Netmiko implementation."""

from typing import Protocol

from app.domains.execution.schemas import AccessMode
from app.tools.network.schemas import CommandResult


class NetworkTool(Protocol):
    def execute(
        self,
        device_id: str,
        access_mode: AccessMode,
        commands: list[str],
    ) -> list[CommandResult]: ...
