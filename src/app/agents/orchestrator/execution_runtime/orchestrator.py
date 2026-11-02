"""Điều phối DAG thực thi; các chi tiết approval và mapping được ủy quyền."""

from datetime import UTC, datetime

from app.agents.network import NetworkAgent, NetworkExecutionResult
from app.agents.orchestrator.execution_runtime.approval import ApprovalGate
from app.agents.orchestrator.execution_runtime.mapping import MappingExecutor
from app.agents.orchestrator.execution_runtime.status import (
    TERMINAL_OPERATION_STATUSES,
    dependencies_satisfied,
    operation_status,
    task_status,
)
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    Operation,
    OperationDeviceStatus,
    OperationStatus,
    TaskDetail,
    TaskStatus,
)
from app.domains.execution.services import ExecutionService


class ExecutionOrchestrator:
    """Thực thi DAG và điều phối các component lưu status/audit."""

    def __init__(
        self,
        execution_service: ExecutionService,
        network_agent: NetworkAgent,
    ) -> None:
        """Khởi tạo approval gate và executor dùng chung cho các mapping."""

        self._execution_service = execution_service
        self._network_agent = network_agent
        self._approval_gate = ApprovalGate(execution_service)
        self._mapping_executor = MappingExecutor(execution_service, network_agent)

    async def execute_task(self, task: TaskDetail) -> list[NetworkExecutionResult]:
        """Chạy Task theo thứ tự DAG và chốt trạng thái cuối."""

        # A late approval callback must not revive a Task already finalized by
        # the approval expiry worker.
        if task.task_status in {
            TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS,
            TaskStatus.FAILED, TaskStatus.REJECTED,
        }:
            return []
        if task.task_status == TaskStatus.RUNNING and (
            self._execution_service.get_task(task.id).task_status in {
                TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS,
                TaskStatus.FAILED, TaskStatus.REJECTED,
            }
        ):
            return []

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
                task.operations,
                key=lambda item: item.display_order,
            ):
                if task.task_status == TaskStatus.RUNNING and (
                    self._execution_service.get_task(task.id).task_status in {
                        TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS,
                        TaskStatus.FAILED, TaskStatus.REJECTED,
                    }
                ):
                    return results
                if operation.operation_status in TERMINAL_OPERATION_STATUSES:
                    statuses[operation.id] = operation.operation_status
                    continue

                dependencies = self._execution_service.list_dependencies(operation.id)
                if not dependencies_satisfied(dependencies, statuses):
                    self._skip_operation(operation)
                    statuses[operation.id] = OperationStatus.SKIPPED
                    continue

                operation_results = await self.execute_network_operation(operation.id)
                results.extend(operation_results)
                persisted = self._execution_service.get_operation(operation.id)
                statuses[operation.id] = persisted.operation_status
                if persisted.operation_status == OperationStatus.WAITING_APPROVAL:
                    self._pause_for_approval(running_task, operation, started_at)
                    return results
        except Exception as exc:
            self._fail_task(running_task, started_at, exc)
            raise

        if task.task_status == TaskStatus.RUNNING and (
            self._execution_service.get_task(task.id).task_status in {
                TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS,
                TaskStatus.FAILED, TaskStatus.REJECTED,
            }
        ):
            return results
        self._complete_task(running_task, started_at, statuses)
        return results

    def load_task_for_operation_device(
        self,
        operation_device_id: str,
    ) -> TaskDetail:
        """Khôi phục Task từ business state để LangGraph tiếp tục sau approval."""

        mapping = self._execution_service.get_operation_device(operation_device_id)
        operation = self._execution_service.get_operation(mapping.operation_id)
        return self._execution_service.get_task(operation.task_id)

    async def execute_network_operation(
        self,
        operation_id: str,
    ) -> list[NetworkExecutionResult]:
        """Chạy một operation trên mọi device mapping và cập nhật status."""

        operation = self._execution_service.get_operation(operation_id)
        mappings = self._execution_service.list_operation_devices(operation_id)
        if not mappings:
            self._skip_operation(operation)
            return []

        operation_started_at = operation.started_at or datetime.now(UTC)
        commands = self._network_agent.extract_commands(
            operation.operation_parameters
        )
        executable_mappings = [
            mapping
            for mapping in mappings
            if self._approval_gate.can_execute(operation, mapping, commands)
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
            await self._mapping_executor.execute(operation, mapping, step_order)
            for step_order, mapping in enumerate(executable_mappings, start=1)
        ]
        current_mappings = self._execution_service.list_operation_devices(operation_id)
        status = operation_status(current_mappings)
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

    def _pause_for_approval(
        self,
        running_task: TaskDetail,
        operation: Operation,
        started_at: datetime,
    ) -> None:
        """Đánh dấu Task đang chờ và ghi activity yêu cầu phê duyệt."""

        self._execution_service.record_activity(
            running_task.id,
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

    def _fail_task(
        self,
        running_task: TaskDetail,
        started_at: datetime,
        error: Exception,
    ) -> None:
        """Chốt Task thất bại và lưu nguyên nhân vào activity timeline."""

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
            running_task.id,
            ActivityActorType.ORCHESTRATOR,
            ActivityEventType.TASK_FAILED,
            ActivityEventStatus.FAILED,
            event_data={"error": str(error)},
        )

    def _complete_task(
        self,
        running_task: TaskDetail,
        started_at: datetime,
        statuses: dict[str, OperationStatus],
    ) -> None:
        """Tổng hợp trạng thái cuối, cập nhật Task và ghi activity kết thúc."""

        final_status = task_status(statuses.values())
        completed_successfully = final_status in {
            TaskStatus.SUCCESS,
            TaskStatus.PARTIAL_SUCCESS,
        }
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
            running_task.id,
            ActivityActorType.ORCHESTRATOR,
            (
                ActivityEventType.TASK_COMPLETED
                if completed_successfully
                else ActivityEventType.TASK_FAILED
            ),
            (
                ActivityEventStatus.SUCCESS
                if completed_successfully
                else ActivityEventStatus.FAILED
            ),
            event_data={"task_status": final_status.value},
        )

    def _skip_operation(self, operation: Operation) -> None:
        """Bỏ qua Operation cùng toàn bộ mapping khi dependency không đạt."""

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
