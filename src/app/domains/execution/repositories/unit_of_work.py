"""Repository facade giữ transaction nguyên tử khi lưu execution plan."""

from datetime import datetime
from typing import Protocol

from app.core.database import create_session_factory
from app.domains.execution.repositories.device_action_log import (
    DeviceActionLogRepository,
)
from app.domains.execution.repositories.operation import (
    OperationRepository,
    OperationRepositoryProtocol,
)
from app.domains.execution.repositories.operation_dependency import (
    OperationDependencyRepository,
)
from app.domains.execution.repositories.operation_device import (
    OperationDeviceRepository,
    OperationDeviceRepositoryProtocol,
)
from app.domains.execution.repositories.operation_device_approval import (
    OperationDeviceApprovalRepository,
    OperationDeviceApprovalRepositoryProtocol,
)
from app.domains.execution.repositories.task import (
    TaskRepository,
    TaskRepositoryProtocol,
)
from app.domains.execution.repositories.task_activity_event import (
    TaskActivityEventRepository,
    TaskActivityEventRepositoryProtocol,
)
from app.domains.execution.repositories.task_execution import TaskExecutionRepository
from app.domains.execution.schemas import (
    ApprovalDecision,
    DeviceActionLog,
    Operation,
    OperationDeviceApproval,
    OperationDependency,
    Task,
    TaskActivityEvent,
    TaskExecution,
    TaskOperationDevice,
)


class ExecutionRepositoryProtocol(
    TaskRepositoryProtocol,
    OperationRepositoryProtocol,
    OperationDeviceRepositoryProtocol,
    TaskActivityEventRepositoryProtocol,
    OperationDeviceApprovalRepositoryProtocol,
    Protocol,
):
    """Contract tổng hợp mà ExecutionService cần cho toàn bộ use case."""

    def save_execution_plan(
        self,
        task: Task,
        operations: list[Operation],
        dependencies: list[OperationDependency],
        operation_devices: list[TaskOperationDevice],
    ) -> None: ...
    def list_dependencies(self, operation_id: str) -> list[OperationDependency]: ...
    def save_task_execution(self, execution: TaskExecution) -> None: ...
    def save_device_action_logs(self, logs: list[DeviceActionLog]) -> None: ...


class ExecutionRepository:
    """Facade cho service và transaction ghi đồng thời nhiều bảng của plan."""

    def __init__(self, database_url: str) -> None:
        # Các repository con sở hữu query của đúng bảng. Facade chỉ chuyển tiếp
        # thao tác đơn bảng và mở transaction cho use case ghi nhiều bảng.
        self._sessions = create_session_factory(database_url)
        self._tasks = TaskRepository(database_url)
        self._operations = OperationRepository(database_url)
        self._operation_devices = OperationDeviceRepository(database_url)
        self._operation_dependencies = OperationDependencyRepository(database_url)
        self._task_executions = TaskExecutionRepository(database_url)
        self._device_action_logs = DeviceActionLogRepository(database_url)
        self._task_activity_events = TaskActivityEventRepository(database_url)
        self._operation_device_approvals = OperationDeviceApprovalRepository(
            database_url
        )

    def save_task(self, task: Task) -> None:
        """Chuyển thao tác bảng tasks tới TaskRepository."""

        self._tasks.save_task(task)

    def get_task(self, task_id: str) -> Task | None:
        """Chuyển truy vấn Task tới TaskRepository."""

        return self._tasks.get_task(task_id)

    def list_tasks(self) -> list[Task]:
        """Chuyển truy vấn danh sách Task tới TaskRepository."""

        return self._tasks.list_tasks()

    def find_task_by_source_message(self, message_id: str) -> Task | None:
        """Chuyển truy vấn source message tới TaskRepository."""

        return self._tasks.find_task_by_source_message(message_id)

    def save_operation(self, operation: Operation) -> None:
        """Chuyển thao tác bảng task_operations tới OperationRepository."""

        self._operations.save_operation(operation)

    def get_operation(self, operation_id: str) -> Operation | None:
        """Chuyển truy vấn operation tới OperationRepository."""

        return self._operations.get_operation(operation_id)

    def list_operations(self, task_id: str) -> list[Operation]:
        """Chuyển truy vấn operations của Task tới OperationRepository."""

        return self._operations.list_operations(task_id)

    def list_operation_devices(
        self,
        operation_id: str,
    ) -> list[TaskOperationDevice]:
        """Chuyển truy vấn mapping tới OperationDeviceRepository."""

        return self._operation_devices.list_operation_devices(operation_id)

    def get_operation_device(
        self,
        operation_device_id: str,
    ) -> TaskOperationDevice | None:
        return self._operation_devices.get_operation_device(operation_device_id)

    def save_operation_device(self, mapping: TaskOperationDevice) -> None:
        self._operation_devices.save_operation_device(mapping)

    def list_dependencies(self, operation_id: str) -> list[OperationDependency]:
        return self._operation_dependencies.list_dependencies(operation_id)

    def save_task_execution(self, execution: TaskExecution) -> None:
        self._task_executions.save(execution)

    def save_device_action_logs(self, logs: list[DeviceActionLog]) -> None:
        self._device_action_logs.add_all(logs)

    def list_task_activity_events(self, task_id: str) -> list[TaskActivityEvent]:
        return self._task_activity_events.list_task_activity_events(task_id)

    def save_task_activity_event(self, event: TaskActivityEvent) -> None:
        self._task_activity_events.save_task_activity_event(event)

    def list_operation_approvals(
        self,
        operation_id: str,
    ) -> list[OperationDeviceApproval]:
        return self._operation_device_approvals.list_operation_approvals(operation_id)

    def get_operation_approval(
        self,
        approval_id: str,
    ) -> OperationDeviceApproval | None:
        return self._operation_device_approvals.get_operation_approval(approval_id)

    def get_operation_device_approval(
        self,
        operation_device_id: str,
    ) -> OperationDeviceApproval | None:
        return self._operation_device_approvals.get_operation_device_approval(
            operation_device_id
        )

    def expire_operation_approval(self, approval_id: str) -> None:
        self._operation_device_approvals.expire_operation_approval(approval_id)

    def decide_operation_approval(
        self,
        approval_id: str,
        user_id: str,
        decision: ApprovalDecision,
        decided_at: datetime,
    ) -> OperationDeviceApproval | None:
        return self._operation_device_approvals.decide_operation_approval(
            approval_id,
            user_id,
            decision,
            decided_at,
        )

    def save_execution_plan(
        self,
        task: Task,
        operations: list[Operation],
        dependencies: list[OperationDependency],
        operation_devices: list[TaskOperationDevice],
    ) -> None:
        """Lưu Task và ba nhóm record của plan trong cùng một transaction."""

        # Nếu bất kỳ bước nào lỗi, context manager rollback cả bốn bảng; không
        # để lại Task PLANNING nhưng thiếu operation/dependency/device mapping.
        with self._sessions.begin() as session:
            TaskRepository.save_in_session(session, task)
            OperationRepository.add_all_in_session(session, operations)
            OperationDependencyRepository.add_all_in_session(session, dependencies)
            OperationDeviceRepository.add_all_in_session(session, operation_devices)
