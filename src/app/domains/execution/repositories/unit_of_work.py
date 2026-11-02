"""Repository facade giữ transaction nguyên tử khi lưu execution plan."""

from datetime import datetime
from app.core.database import create_session_factory
from app.domains.execution.repositories.device_action_log import (
    DeviceActionLogRepository,
)
from app.domains.execution.repositories.operation import OperationRepository
from app.domains.execution.repositories.operation_dependency import (
    OperationDependencyRepository,
)
from app.domains.execution.repositories.operation_device import OperationDeviceRepository
from app.domains.execution.repositories.operation_device_approval import OperationDeviceApprovalRepository
from app.domains.execution.repositories.task import TaskRepository
from app.domains.execution.repositories.task_activity_event import TaskActivityEventRepository
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

    def get_task_by_id(self, task_id: str) -> Task | None:
        """Chuyển truy vấn Task tới TaskRepository."""

        return self._tasks.get_by_id(task_id)

    def get_all_tasks(self) -> list[Task]:
        """Chuyển truy vấn danh sách Task tới TaskRepository."""

        return self._tasks.get_all()

    def get_task_by_source_message_id(self, message_id: str) -> Task | None:
        """Chuyển truy vấn source message tới TaskRepository."""

        return self._tasks.get_by_source_message_id(message_id)

    def save_operation(self, operation: Operation) -> None:
        """Chuyển thao tác bảng task_operations tới OperationRepository."""

        self._operations.save_operation(operation)

    def get_operation_by_id(self, operation_id: str) -> Operation | None:
        """Chuyển truy vấn operation tới OperationRepository."""

        return self._operations.get_by_id(operation_id)

    def get_all_operations_by_task_id(self, task_id: str) -> list[Operation]:
        """Chuyển truy vấn operations của Task tới OperationRepository."""

        return self._operations.get_all_by_task_id(task_id)

    def get_all_operation_devices_by_operation_id(
        self,
        operation_id: str,
    ) -> list[TaskOperationDevice]:
        """Chuyển truy vấn mapping tới OperationDeviceRepository."""

        return self._operation_devices.get_all_by_operation_id(operation_id)

    def get_operation_device_by_id(
        self,
        operation_device_id: str,
    ) -> TaskOperationDevice | None:
        return self._operation_devices.get_by_id(operation_device_id)

    def save_operation_device(self, mapping: TaskOperationDevice) -> None:
        self._operation_devices.save_operation_device(mapping)

    def get_all_dependencies_by_operation_id(
        self,
        operation_id: str,
    ) -> list[OperationDependency]:
        return self._operation_dependencies.get_all_by_operation_id(operation_id)

    def save_task_execution(self, execution: TaskExecution) -> None:
        self._task_executions.save(execution)

    def save_device_action_logs(self, logs: list[DeviceActionLog]) -> None:
        self._device_action_logs.save_all(logs)

    def get_recent_device_action_logs(
        self,
        limit: int = 500,
    ) -> list[DeviceActionLog]:
        return self._device_action_logs.get_recent(limit)

    def get_all_task_activity_events_by_task_id(
        self,
        task_id: str,
    ) -> list[TaskActivityEvent]:
        return self._task_activity_events.get_all_by_task_id(task_id)

    def save_task_activity_event(self, event: TaskActivityEvent) -> None:
        self._task_activity_events.save_task_activity_event(event)

    def get_all_operation_approvals_by_operation_id(
        self,
        operation_id: str,
    ) -> list[OperationDeviceApproval]:
        return self._operation_device_approvals.get_all_by_operation_id(operation_id)

    def save_operation_device_approval(
        self,
        approval: OperationDeviceApproval,
    ) -> None:
        self._operation_device_approvals.save_operation_device_approval(approval)

    def get_operation_approval_by_id(
        self,
        approval_id: str,
    ) -> OperationDeviceApproval | None:
        return self._operation_device_approvals.get_by_id(approval_id)

    def get_approval_by_operation_device_id(
        self,
        operation_device_id: str,
    ) -> OperationDeviceApproval | None:
        return self._operation_device_approvals.get_by_operation_device_id(
            operation_device_id
        )

    def expire_operation_approval(self, approval_id: str) -> None:
        self._operation_device_approvals.expire_operation_approval(approval_id)

    def decide_operation_approval(
        self,
        approval_id: str,
        *,
        user_id: str,
        decision: ApprovalDecision,
        decided_at: datetime,
    ) -> OperationDeviceApproval | None:
        return self._operation_device_approvals.decide_operation_approval(
            approval_id,
            user_id=user_id,
            decision=decision,
            decided_at=decided_at,
        )

    def save_execution_plan(
        self,
        task: Task,
        *,
        operations: list[Operation],
        dependencies: list[OperationDependency],
        operation_devices: list[TaskOperationDevice],
    ) -> None:
        """Lưu Task và ba nhóm record của plan trong cùng một transaction."""

        # Nếu bất kỳ bước nào lỗi, context manager rollback cả bốn bảng; không
        # để lại Task PLANNING nhưng thiếu operation/dependency/device mapping.
        with self._sessions.begin() as session:
            TaskRepository.save_in_session(session, task)
            OperationRepository.save_all_in_session(session, operations)
            # Các dependency và device mapping đều tham chiếu operation mới.
            # Flush operation trước để PostgreSQL nhìn thấy khóa cha trong cùng
            # transaction, đặc biệt với plan có nhiều dependency.
            session.flush()
            OperationDependencyRepository.save_all_in_session(session, dependencies)
            OperationDeviceRepository.save_all_in_session(session, operation_devices)
