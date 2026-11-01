"""Thực thi một operation-device mapping và ghi execution/audit log."""

from datetime import UTC, datetime
from time import monotonic

from app.agents.network import (
    NetworkAgent,
    NetworkExecutionResult,
    NetworkExecutionStatus,
)
from app.core.utils import IdPrefix, generate_id, generate_uuid
from app.domains.execution.schemas import (
    AccessMode,
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    DeviceActionLog,
    DeviceActionPhase,
    DeviceActionStatus,
    DeviceActionType,
    ExecutionStatus,
    Operation,
    OperationDeviceStatus,
    TaskExecution,
    TaskOperationDevice,
)
from app.domains.execution.services import ExecutionService


class MappingExecutor:
    """Cô lập vòng đời thực thi và audit của một device mapping."""

    def __init__(
        self,
        execution_service: ExecutionService,
        network_agent: NetworkAgent,
    ) -> None:
        """Khởi tạo service lưu trạng thái và Network Agent thực thi lệnh."""

        self._execution_service = execution_service
        self._network_agent = network_agent

    async def execute(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        step_order: int,
    ) -> NetworkExecutionResult:
        """Thực thi một mapping và lưu đầy đủ trạng thái, output cùng audit."""

        started_at = datetime.now(UTC)
        started_clock = monotonic()
        commands = self._network_agent.extract_commands(operation.operation_parameters)
        running_mapping = mapping.model_copy(
            update={
                "operation_device_status": OperationDeviceStatus.RUNNING,
                "error_message": None,
                "started_at": started_at,
                "completed_at": None,
            }
        )
        self._execution_service.update_operation_device(running_mapping)

        execution = self._new_execution(
            operation,
            mapping,
            commands,
            step_order,
            started_at,
        )
        self._execution_service.save_task_execution(execution)

        result = await self._network_agent.execute(operation, mapping)
        completed_at = datetime.now(UTC)
        succeeded = result.status == NetworkExecutionStatus.SUCCESS
        self._execution_service.update_operation_device(
            running_mapping.model_copy(
                update={
                    "operation_device_status": (
                        OperationDeviceStatus.SUCCESS
                        if succeeded
                        else OperationDeviceStatus.FAILED
                    ),
                    "error_message": None if succeeded else result.error_message,
                    "completed_at": completed_at,
                }
            )
        )

        completed_execution = execution.model_copy(
            update={
                "output": [item.model_dump(mode="json") for item in result.results],
                "execution_status": (
                    ExecutionStatus.SUCCESS if succeeded else ExecutionStatus.FAILED
                ),
                "error_message": None if succeeded else result.error_message,
                "completed_at": completed_at,
                "duration_ms": max(0, int((monotonic() - started_clock) * 1000)),
            }
        )
        self._execution_service.save_task_execution(completed_execution)
        self._execution_service.save_device_action_logs(
            build_action_logs(
                operation,
                mapping,
                completed_execution,
                commands,
                result,
                completed_at,
            )
        )
        self._record_activity(
            operation,
            mapping,
            execution,
            commands,
            result,
            started_at,
            completed_at,
        )
        return result

    def _new_execution(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        commands: list[str],
        step_order: int,
        started_at: datetime,
    ) -> TaskExecution:
        """Tạo bản ghi TaskExecution ở trạng thái RUNNING trước khi gọi agent."""

        return TaskExecution(
            id=generate_id(IdPrefix.TASK_EXECUTION),
            task_id=operation.task_id,
            operation_id=operation.id,
            operation_device_id=mapping.id,
            agent_name=self._network_agent.name,
            tool_name=self._network_agent.tool_name,
            step_order=step_order,
            input={
                "device_id": mapping.device_id,
                "access_mode": mapping.access_mode.value,
                "commands": commands,
            },
            execution_status=ExecutionStatus.RUNNING,
            started_at=started_at,
            created_at=started_at,
        )

    def _record_activity(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        execution: TaskExecution,
        commands: list[str],
        result: NetworkExecutionResult,
        started_at: datetime,
        completed_at: datetime,
    ) -> None:
        """Ghi activity COMMAND_EXECUTED kèm thời gian và kết quả thực thi."""

        succeeded = result.status == NetworkExecutionStatus.SUCCESS
        self._execution_service.record_activity(
            operation.task_id,
            ActivityActorType.NETWORK,
            ActivityEventType.COMMAND_EXECUTED,
            ActivityEventStatus.SUCCESS if succeeded else ActivityEventStatus.FAILED,
            operation_id=operation.id,
            execution_id=execution.id,
            event_data={
                "device_id": mapping.device_id,
                "command_count": len(commands),
                "error": result.error_message,
            },
            started_at=started_at,
            completed_at=completed_at,
        )


def build_action_logs(
    operation: Operation,
    mapping: TaskOperationDevice,
    execution: TaskExecution,
    commands: list[str],
    result: NetworkExecutionResult,
    executed_at: datetime,
) -> list[DeviceActionLog]:
    """Tạo audit log cho các command đã thực sự có output từ backend mạng."""

    succeeded = result.status == NetworkExecutionStatus.SUCCESS
    outputs = [item.output for item in result.results]
    if not succeeded and not outputs:
        return []

    action_type = (
        DeviceActionType.READ
        if mapping.access_mode == AccessMode.READ
        else DeviceActionType.WRITE
    )
    action_phase = (
        DeviceActionPhase.READ
        if mapping.access_mode == AccessMode.READ
        else DeviceActionPhase.APPLY
    )
    return [
        DeviceActionLog(
            id=generate_uuid(),
            task_id=operation.task_id,
            operation_id=operation.id,
            operation_device_id=mapping.id,
            execution_id=execution.id,
            device_id=mapping.device_id,
            action_type=action_type,
            action_phase=action_phase,
            sequence_number=sequence,
            command=command,
            result=(
                outputs[sequence - 1]
                if sequence <= len(outputs)
                else (outputs[0] if outputs else None)
            ),
            action_log_status=(
                DeviceActionStatus.SUCCESS
                if succeeded
                else DeviceActionStatus.FAILED
            ),
            error_message=None if succeeded else result.error_message,
            executed_at=executed_at,
        )
        for sequence, command in enumerate(commands, start=1)
    ]
