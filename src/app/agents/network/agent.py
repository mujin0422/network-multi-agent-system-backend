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

    # Thực thi command được Planner đặt trong operation_parameters.
    async def execute(
        self,
        operation: Operation,
        operation_device: TaskOperationDevice,
    ) -> NetworkExecutionResult:
        """Thực thi command được Planner đặt trong operation_parameters."""

        if operation_device.operation_id != operation.id:
            raise ValueError("TaskOperationDevice không thuộc Operation")

        commands = self.extract_commands(operation.operation_parameters)
        try:
            results = await asyncio.to_thread(
                self._tool.execute,
                operation_device.device_id,
                operation_device.access_mode,
                commands,
            )
            return NetworkExecutionResult(
                operation_id=operation.id,
                operation_device_id=operation_device.id,
                device_id=operation_device.device_id,
                access_mode=operation_device.access_mode,
                status=NetworkExecutionStatus.SUCCESS,
                results=results,
            )
        except Exception as exc:
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
        if not commands:
            raise ValueError("Operation không chứa command hợp lệ")
        return commands
