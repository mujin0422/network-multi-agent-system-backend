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
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    ApprovalStatus,
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
from app.domains.execution.utils import build_approval_request_hash


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
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ORCHESTRATOR,
            ActivityEventType.EXECUTION_STARTED,
        )
        results: list[NetworkExecutionResult] = []
        statuses: dict[str, OperationStatus] = {}

        try:
            for operation in sorted(
                task.operations, key=lambda item: item.display_order
            ):
                if operation.operation_status in {
                    OperationStatus.SUCCESS,
                    OperationStatus.PARTIAL_SUCCESS,
                    OperationStatus.FAILED,
                    OperationStatus.REJECTED,
                    OperationStatus.SKIPPED,
                }:
                    statuses[operation.id] = operation.operation_status
                    continue
                dependencies = self._execution_service.list_dependencies(operation.id)
                if not self._dependencies_satisfied(dependencies, statuses):
                    self._skip_operation(operation)
                    statuses[operation.id] = OperationStatus.SKIPPED
                    continue
                operation_results = await self.execute_network_operation(operation.id)
                results.extend(operation_results)
                persisted = self._execution_service.get_operation(operation.id)
                statuses[operation.id] = persisted.operation_status
                if persisted.operation_status == OperationStatus.WAITING_APPROVAL:
                    # Task tạm dừng tại đây. Không SKIP operation phía sau vì
                    # dependency của chúng chưa thất bại; chỉ chưa được duyệt.
                    self._execution_service.record_activity(
                        task.id,
                        ActivityActorType.ORCHESTRATOR,
                        ActivityEventType.APPROVAL_REQUESTED,
                        ActivityEventStatus.WAITING_APPROVAL,
                        operation_id=operation.id,
                    )
                    self._execution_service.update_task(
                        running_task.model_copy(
                            update={
                                "started_at": running_task.started_at or started_at,
                                "completed_at": None,
                            }
                        )
                    )
                    return results
        except Exception as exc:
            self._execution_service.update_task(
                running_task.model_copy(
                    update={
                        "task_status": TaskStatus.FAILED,
                        "started_at": running_task.started_at or started_at,
                        "completed_at": datetime.now(UTC),
                    }
                )
            )
            self._execution_service.record_activity(
                task.id,
                ActivityActorType.ORCHESTRATOR,
                ActivityEventType.TASK_FAILED,
                ActivityEventStatus.FAILED,
                event_data={"error": str(exc)},
            )
            raise

        final_status = self._task_status(statuses.values())
        self._execution_service.update_task(
            running_task.model_copy(
                update={
                    "task_status": final_status,
                    "started_at": running_task.started_at or started_at,
                    "completed_at": datetime.now(UTC),
                }
            )
        )
        self._execution_service.record_activity(
            task.id,
            ActivityActorType.ORCHESTRATOR,
            (
                ActivityEventType.TASK_COMPLETED
                if final_status in {TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS}
                else ActivityEventType.TASK_FAILED
            ),
            (
                ActivityEventStatus.SUCCESS
                if final_status in {TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS}
                else ActivityEventStatus.FAILED
            ),
            event_data={"task_status": final_status.value},
        )
        return results

    async def resume_after_approval(
        self,
        operation_device_id: str,
    ) -> list[NetworkExecutionResult]:
        """Đọc lại Task và tiếp tục DAG sau quyết định của người dùng."""

        mapping = self._execution_service.get_operation_device(operation_device_id)
        operation = self._execution_service.get_operation(mapping.operation_id)
        task = self._execution_service.get_task(operation.task_id)
        return await self.execute_task(task)

    async def execute_network_operation(
        self, operation_id: str
    ) -> list[NetworkExecutionResult]:
        """Chạy một operation trên mọi device mapping và ghi audit."""

        operation = self._execution_service.get_operation(operation_id)
        mappings = self._execution_service.list_operation_devices(operation_id)
        if not mappings:
            self._skip_operation(operation)
            return []

        operation_started_at = operation.started_at or datetime.now(UTC)
        commands = self._network_agent.extract_commands(operation.operation_parameters)
        executable_mappings = [
            mapping
            for mapping in mappings
            if self._mapping_can_execute(operation, mapping, commands)
        ]

        if executable_mappings:
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
            for step_order, mapping in enumerate(executable_mappings, start=1)
        ]
        current_mappings = self._execution_service.list_operation_devices(operation_id)
        status = self._operation_status(current_mappings)
        self._execution_service.update_operation(
            operation.model_copy(
                update={
                    "operation_status": status,
                    "started_at": operation_started_at,
                    "completed_at": (
                        None
                        if status == OperationStatus.WAITING_APPROVAL
                        else datetime.now(UTC)
                    ),
                }
            )
        )
        return results

    def _mapping_can_execute(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        commands: list[str],
    ) -> bool:
        """Áp dụng approval gate trước khi Network Agent thấy lệnh WRITE."""

        if mapping.operation_device_status in {
            OperationDeviceStatus.SUCCESS,
            OperationDeviceStatus.REJECTED,
            OperationDeviceStatus.SKIPPED,
        }:
            return False
        if mapping.access_mode == AccessMode.READ:
            return True

        approval = self._execution_service.get_operation_device_approval(mapping.id)
        if approval is None:
            self._execution_service.create_operation_device_approval(
                operation,
                mapping,
                commands,
                build_approval_request_hash(mapping.id, commands),
            )
            self._wait_for_approval(mapping, None)
            return False

        now = datetime.now(UTC)
        if approval.approval_status == ApprovalStatus.PENDING:
            if approval.expires_at is not None and approval.expires_at <= now:
                self._execution_service.expire_operation_approval(approval.id)
                self._reject_mapping(mapping, "Yêu cầu phê duyệt đã hết hạn")
            else:
                self._wait_for_approval(mapping, None)
            return False
        if approval.approval_status in {
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
        }:
            self._reject_mapping(mapping, "Cấu hình không được phê duyệt")
            return False

        expected_hash = build_approval_request_hash(mapping.id, commands)
        if (
            approval.commands_snapshot != commands
            or approval.request_hash != expected_hash
        ):
            self._fail_mapping(
                mapping,
                "Command hiện tại không khớp snapshot đã được phê duyệt",
            )
            return False
        return True

    def _wait_for_approval(
        self,
        mapping: TaskOperationDevice,
        error_message: str | None,
    ) -> None:
        self._execution_service.update_operation_device(
            mapping.model_copy(
                update={
                    "operation_device_status": OperationDeviceStatus.WAITING_APPROVAL,
                    "error_message": error_message,
                    "completed_at": None,
                }
            )
        )

    def _reject_mapping(
        self,
        mapping: TaskOperationDevice,
        error_message: str,
    ) -> None:
        self._execution_service.update_operation_device(
            mapping.model_copy(
                update={
                    "operation_device_status": OperationDeviceStatus.REJECTED,
                    "error_message": error_message,
                    "completed_at": datetime.now(UTC),
                }
            )
        )

    def _fail_mapping(
        self,
        mapping: TaskOperationDevice,
        error_message: str,
    ) -> None:
        self._execution_service.update_operation_device(
            mapping.model_copy(
                update={
                    "operation_device_status": OperationDeviceStatus.FAILED,
                    "error_message": error_message,
                    "completed_at": datetime.now(UTC),
                }
            )
        )

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
        if values and all(value == OperationStatus.REJECTED for value in values):
            return TaskStatus.REJECTED
        return TaskStatus.FAILED

    @staticmethod
    def _operation_status(mappings: list[TaskOperationDevice]) -> OperationStatus:
        statuses = [mapping.operation_device_status for mapping in mappings]
        if OperationDeviceStatus.WAITING_APPROVAL in statuses:
            return OperationStatus.WAITING_APPROVAL
        if statuses and all(status == OperationDeviceStatus.SUCCESS for status in statuses):
            return OperationStatus.SUCCESS
        if statuses and all(status == OperationDeviceStatus.REJECTED for status in statuses):
            return OperationStatus.REJECTED
        if OperationDeviceStatus.SUCCESS in statuses:
            return OperationStatus.PARTIAL_SUCCESS
        return OperationStatus.FAILED
