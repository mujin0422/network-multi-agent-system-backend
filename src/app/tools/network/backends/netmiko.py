"""Backend thực thi trực tiếp bằng Netmiko."""

from typing import Any

from app.domains.execution.schemas import AccessMode
from app.domains.inventory.services import NetworkService
from app.tools.network.schemas import CommandResult


class NetmikoNetworkTool:
    """Kết nối, chạy command và luôn đóng phiên thiết bị."""

    def __init__(self, network_service: NetworkService) -> None:
        self._network_service = network_service

    def execute(
        self,
        device_id: str,
        access_mode: AccessMode,
        commands: list[str],
    ) -> list[CommandResult]:
        connection_result = self._network_service.connect(device_id)
        if not connection_result.get("success"):
            raise ConnectionError(
                connection_result.get("error", "Không thể kết nối thiết bị")
            )

        connection: Any = connection_result["connection"]
        try:
            if access_mode == AccessMode.WRITE:
                output = connection.send_config_set(commands)
                return [
                    CommandResult(command="\n".join(commands), output=str(output))
                ]
            return [
                CommandResult(
                    command=command,
                    output=str(connection.send_command(command)),
                )
                for command in commands
            ]
        finally:
            connection.disconnect()
