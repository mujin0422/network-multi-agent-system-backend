"""Public service cho vòng đời Task, Operation và ChangeSet."""

from datetime import UTC, datetime

from app.core.errors import (
    InvalidStateTransitionError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.core.ids import generate_id
from app.domains.execution.repository import ExecutionRepository
from app.domains.execution.schemas import (
    ChangeSet,
    ChangeSetApproval,
    ChangeSetCreate,
    ChangeSetStatus,
    Operation,
    OperationCreate,
    OperationStatus,
    Task,
    TaskCreate,
    TaskDetail,
    TaskStatus,
)


class ExecutionService:
    def __init__(self, repository: ExecutionRepository) -> None:
        self._repository = repository

    def create_task(self, payload: TaskCreate) -> Task:
        # source_message_id là UNIQUE: một message người dùng chỉ sinh một Task.
        if self._repository.find_task_by_source_message(payload.source_message_id):
            raise ResourceConflictError(
                f"Message '{payload.source_message_id}' đã tạo Task trước đó"
            )
        task = Task(
            id=generate_id("task"),
            **payload.model_dump(),
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        self._repository.save_task(task)
        return task

    def list_tasks(self) -> list[Task]:
        return self._repository.list_tasks()

    def get_task(self, task_id: str) -> TaskDetail:
        task = self._require_task(task_id)
        return TaskDetail(
            **task.model_dump(),
            operations=self._repository.list_operations(task_id),
        )

    def add_operation(self, task_id: str, payload: OperationCreate) -> Operation:
        task = self._require_task(task_id)
        if task.status not in {TaskStatus.PENDING, TaskStatus.PLANNING}:
            raise InvalidStateTransitionError(
                f"Không thể thêm operation khi Task đang ở trạng thái {task.status}"
            )
        operation = Operation(
            id=generate_id("oper"),
            task_id=task_id,
            **payload.model_dump(),
            status=OperationStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        self._repository.save_operation(operation)
        if task.status == TaskStatus.PENDING:
            self._repository.save_task(
                task.model_copy(update={"status": TaskStatus.PLANNING})
            )
        return operation

    def create_change_set(
        self,
        operation_id: str,
        payload: ChangeSetCreate,
    ) -> ChangeSet:
        operation = self._require_operation(operation_id)
        if operation.status not in {
            OperationStatus.PENDING,
            OperationStatus.WAITING_APPROVAL,
        }:
            raise InvalidStateTransitionError(
                "Operation hiện tại không cho phép tạo thêm ChangeSet"
            )
        if self._repository.find_change_set(operation_id, payload.device_id):
            raise ResourceConflictError(
                "Operation đã có ChangeSet cho device "
                f"'{payload.device_id}'"
            )
        change_set = ChangeSet(
            id=generate_id("chgs"),
            operation_id=operation_id,
            **payload.model_dump(),
            status=ChangeSetStatus.WAITING_APPROVAL,
            created_at=datetime.now(UTC),
        )
        self._repository.save_change_set(change_set)
        # Một Operation có thể tác động nhiều device. Mỗi device có ChangeSet riêng,
        # còn trạng thái Operation giữ WAITING_APPROVAL cho tới khi kế hoạch được duyệt.
        if operation.status == OperationStatus.PENDING:
            self._repository.save_operation(
                operation.model_copy(update={"status": OperationStatus.WAITING_APPROVAL})
            )
        return change_set

    def approve_change_set(
        self,
        change_set_id: str,
        payload: ChangeSetApproval,
    ) -> ChangeSet:
        change_set = self._require_change_set(change_set_id)
        if change_set.status != ChangeSetStatus.WAITING_APPROVAL:
            raise InvalidStateTransitionError(
                f"Không thể approve ChangeSet ở trạng thái {change_set.status}"
            )
        approved = change_set.model_copy(
            update={
                "status": ChangeSetStatus.APPROVED,
                "approved_by": payload.approved_by,
                "approved_at": datetime.now(UTC),
            }
        )
        self._repository.save_change_set(approved)
        return approved

    def _require_task(self, task_id: str) -> Task:
        task = self._repository.get_task(task_id)
        if task is None:
            raise ResourceNotFoundError(f"Không tìm thấy Task '{task_id}'")
        return task

    def _require_operation(self, operation_id: str) -> Operation:
        operation = self._repository.get_operation(operation_id)
        if operation is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy Operation '{operation_id}'"
            )
        return operation

    def _require_change_set(self, change_set_id: str) -> ChangeSet:
        change_set = self._repository.get_change_set(change_set_id)
        if change_set is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy ChangeSet '{change_set_id}'"
            )
        return change_set
