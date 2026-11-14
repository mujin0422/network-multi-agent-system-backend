"""Network Agent thực thi operation trên thiết bị, không phân tích dữ liệu."""

import asyncio

from app.agents.network.schemas import (
    NetworkExecutionResult,
    NetworkExecutionStatus,
)
from app.domains.execution.schemas import Operation, TaskOperationDevice
from app.tools import NetworkTool


class NetworkAgent:
    name = "network-agent"

    def __init__(self, tool: NetworkTool) -> None:
        self._tool = tool

    @property
    def tool_name(self) -> str:
        """Tên backend được ghi vào task_executions."""

        return type(self._tool).__name__

    async def execute(
        self,
        operation: Operation,
        operation_device: TaskOperationDevice,
    ) -> NetworkExecutionResult:
        """Thực thi command đã được lập kế hoạch và kiểm tra."""

        # Bước 1: Bảo đảm mapping thuộc đúng Operation đang thực thi.
        if operation_device.operation_id != operation.id:
            raise ValueError("TaskOperationDevice không thuộc Operation")

        # Bước 2: Trích xuất danh sách command hợp lệ từ operation parameters.
        commands = self.extract_commands(operation.operation_parameters)
        try:
            # Bước 3: Gọi NetworkTool trong thread riêng để không chặn event loop.
            results = await asyncio.to_thread(
                self._tool.execute,
                operation_device.device_id,
                operation_device.access_mode,
                commands,
            )
            # Bước 4: Chuẩn hóa output thành kết quả thực thi thành công.
            return NetworkExecutionResult(
                operation_id=operation.id,
                operation_device_id=operation_device.id,
                device_id=operation_device.device_id,
                access_mode=operation_device.access_mode,
                status=NetworkExecutionStatus.SUCCESS,
                results=results,
            )
        except Exception as exc:
            # Bước 5: Chuyển lỗi công cụ thành kết quả thất bại có cấu trúc.
            return NetworkExecutionResult(
                operation_id=operation.id,
                operation_device_id=operation_device.id,
                device_id=operation_device.device_id,
                access_mode=operation_device.access_mode,
                status=NetworkExecutionStatus.FAILED,
                error_message=str(exc),
            )

    @staticmethod
    def extract_commands(parameters: dict) -> list[str]:
        # Bước 1: Chấp nhận cả command đơn và danh sách commands.
        raw_commands = parameters.get("commands", parameters.get("command"))
        if isinstance(raw_commands, str):
            commands = [raw_commands.strip()]
        elif isinstance(raw_commands, list):
            commands = [
                command.strip()
                for command in raw_commands
                if isinstance(command, str) and command.strip()
            ]
        else:
            commands = []
        # Bước 2: Từ chối Operation không có command thực thi hợp lệ.
        if not commands:
            raise ValueError("Operation không chứa command hợp lệ")
        return commands
