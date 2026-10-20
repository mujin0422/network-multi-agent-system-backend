"""Điều phối và ghi nhận vòng đời thực thi network Task."""

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
    DependencyType,
    DeviceActionLog,
    DeviceActionPhase,
    DeviceActionStatus,
    DeviceActionType,
    ExecutionStatus,
    Operation,
    OperationDeviceStatus,
    OperationStatus,
    TaskDetail,
    TaskExecution,
    TaskOperationDevice,
    TaskStatus,
)
from app.domains.execution.services import ExecutionService


class ExecutionOrchestrator:
    """Thực thi DAG và lưu status/audit theo database design."""

    def __init__(
        self, execution_service: ExecutionService, network_agent: NetworkAgent
    ) -> None:
        self._execution_service = execution_service
        self._network_agent = network_agent

    async def execute_task(self, task: TaskDetail) -> list[NetworkExecutionResult]:
        """Chạy Task theo thứ tự DAG và chốt trạng thái cuối."""

        started_at = datetime.now(UTC)
        running_task = task.model_copy(
            update={"task_status": TaskStatus.RUNNING, "completed_at": None}
        )
        self._execution_service.update_task(running_task)
        results: list[NetworkExecutionResult] = []
        statuses: dict[str, OperationStatus] = {}

        try:
            for operation in sorted(
                task.operations, key=lambda item: item.display_order
            ):
                dependencies = self._execution_service.list_dependencies(operation.id)
                if not self._dependencies_satisfied(dependencies, statuses):
                    self._skip_operation(operation)
                    statuses[operation.id] = OperationStatus.SKIPPED
                    continue
                operation_results = await self.execute_network_operation(operation.id)
                results.extend(operation_results)
                persisted = self._execution_service.get_operation(operation.id)
                statuses[operation.id] = persisted.operation_status
        except Exception:
            self._execution_service.update_task(
                running_task.model_copy(
                    update={
                        "task_status": TaskStatus.FAILED,
                        "started_at": running_task.started_at or started_at,
                        "completed_at": datetime.now(UTC),
                    }
                )
            )
            raise

        self._execution_service.update_task(
            running_task.model_copy(
                update={
                    "task_status": self._task_status(statuses.values()),
                    "started_at": running_task.started_at or started_at,
                    "completed_at": datetime.now(UTC),
                }
            )
        )
        return results

    async def execute_network_operation(
        self, operation_id: str
    ) -> list[NetworkExecutionResult]:
        """Chạy một operation trên mọi device mapping và ghi audit."""

        operation = self._execution_service.get_operation(operation_id)
        mappings = self._execution_service.list_operation_devices(operation_id)
        if not mappings:
            self._skip_operation(operation)
            return []

        operation_started_at = datetime.now(UTC)
        self._execution_service.update_operation(
            operation.model_copy(
                update={
                    "operation_status": OperationStatus.RUNNING,
                    "started_at": operation_started_at,
                    "completed_at": None,
                }
            )
        )
        results = [
            await self._execute_mapping(operation, mapping, step_order)
            for step_order, mapping in enumerate(mappings, start=1)
        ]
        success_count = sum(
            result.status == NetworkExecutionStatus.SUCCESS for result in results
        )
        status = (
            OperationStatus.SUCCESS
            if success_count == len(results)
            else OperationStatus.PARTIAL_SUCCESS
            if success_count
            else OperationStatus.FAILED
        )
        self._execution_service.update_operation(
            operation.model_copy(
                update={
                    "operation_status": status,
                    "started_at": operation_started_at,
                    "completed_at": datetime.now(UTC),
                }
            )
        )
        return results

    async def _execute_mapping(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        step_order: int,
    ) -> NetworkExecutionResult:
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
        execution = TaskExecution(
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
            self._build_action_logs(
                operation, mapping, completed_execution, commands, result, completed_at
            )
        )
        return result

    @staticmethod
    def _build_action_logs(
        operation: Operation,
        mapping: TaskOperationDevice,
        execution: TaskExecution,
        commands: list[str],
        result: NetworkExecutionResult,
        executed_at: datetime,
    ) -> list[DeviceActionLog]:
        succeeded = result.status == NetworkExecutionStatus.SUCCESS
        outputs = [item.output for item in result.results]
        # Khi backend không trả CommandResult, không thể khẳng định
        # command đã được gửi. Lỗi đó vẫn nằm trong task_executions
        # và mapping; không tạo device_action_logs sai sự thật.
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

    def _skip_operation(self, operation: Operation) -> None:
        completed_at = datetime.now(UTC)
        self._execution_service.update_operation(
            operation.model_copy(
                update={
                    "operation_status": OperationStatus.SKIPPED,
                    "completed_at": completed_at,
                }
            )
        )
        for mapping in self._execution_service.list_operation_devices(operation.id):
            self._execution_service.update_operation_device(
                mapping.model_copy(
                    update={
                        "operation_device_status": OperationDeviceStatus.SKIPPED,
                        "completed_at": completed_at,
                    }
                )
            )

    @staticmethod
    def _dependencies_satisfied(dependencies, statuses) -> bool:
        for dependency in dependencies:
            status = statuses.get(dependency.depends_on_operation_id)
            if dependency.dependency_type == DependencyType.ON_SUCCESS:
                if status != OperationStatus.SUCCESS:
                    return False
            elif status not in {
                OperationStatus.SUCCESS,
                OperationStatus.PARTIAL_SUCCESS,
                OperationStatus.FAILED,
                OperationStatus.REJECTED,
                OperationStatus.SKIPPED,
            }:
                return False
        return True

    @staticmethod
    def _task_status(statuses) -> TaskStatus:
        values = list(statuses)
        if values and all(value == OperationStatus.SUCCESS for value in values):
            return TaskStatus.SUCCESS
        if any(
            value in {OperationStatus.SUCCESS, OperationStatus.PARTIAL_SUCCESS}
            for value in values
        ):
            return TaskStatus.PARTIAL_SUCCESS
        return TaskStatus.FAILED
