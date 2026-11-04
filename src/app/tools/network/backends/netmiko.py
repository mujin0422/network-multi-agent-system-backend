"""Backend thực thi trực tiếp bằng Netmiko."""

import re
from typing import Any

from app.domains.execution.schemas import AccessMode
from app.domains.inventory.services import NetworkService
from app.tools.network.commands import normalize_config_commands
from app.tools.network.schemas import CommandResult


class NetmikoNetworkTool:
    """Kết nối, chạy command và luôn đóng phiên thiết bị."""

    _CONFIG_ERROR_PATTERN = re.compile(
        r"^%\s*(?:Invalid input|Incomplete command|Ambiguous command|Unknown command|Error)",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    def __init__(
        self,
        network_service: NetworkService,
        read_timeout: float = 60.0,
        cmd_verify: bool = False,
    ) -> None:
        self._network_service = network_service
        self._read_timeout = read_timeout
        self._cmd_verify = cmd_verify

    def execute(
        self,
        device_id: str,
        access_mode: AccessMode,
        commands: list[str],
    ) -> list[CommandResult]:
        # Bước 1: Lấy credential an toàn và mở một connection riêng cho lần gọi.
        connection_result = self._network_service.connect(device_id)
        if not connection_result.get("success"):
            raise ConnectionError(
                connection_result.get("error", "Không thể kết nối thiết bị")
            )

        connection: Any = connection_result["connection"]
        try:
            if access_mode == AccessMode.WRITE:
                # Bước 2: Chuẩn hóa command cấu hình trước khi gửi vào config mode.
                commands = normalize_config_commands(commands)
                output = connection.send_config_set(
                    commands,
                    read_timeout=self._read_timeout,
                    cmd_verify=self._cmd_verify,
                )
                # Bước 3: Phát hiện lỗi CLI dù Netmiko không ném exception.
                error_match = self._CONFIG_ERROR_PATTERN.search(str(output))
                if error_match:
                    output_lines = str(output).splitlines()
                    error_line = str(output)[: error_match.start()].count("\n")
                    context = "\n".join(
                        output_lines[max(0, error_line - 2) : error_line + 2]
                    )
                    raise RuntimeError(
                        "Thiết bị từ chối lệnh cấu hình:\n"
                        f"{context or error_match.group(0)}"
                    )
                # Bước 4: Chỉ lưu cấu hình khi toàn bộ output không có lỗi CLI.
                connection.save_config()
                return [
                    CommandResult(command="\n".join(commands), output=str(output))
                ]
            # Bước 2: Với READ, chạy từng command và giữ nguyên output làm evidence.
            return [
                CommandResult(
                    command=command,
                    output=str(
                        connection.send_command(
                            command,
                            read_timeout=self._read_timeout,
                        )
                    ),
                )
                for command in commands
            ]
        finally:
            # Bước 5: Luôn đóng session để retry sau dùng connection sạch.
            connection.disconnect()
