"""Public service cho vòng đời Task và Operation."""

from datetime import UTC, datetime

from app.core.exceptions import (
    InvalidStateTransitionError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.core.utils import generate_id
from app.domains.execution.repositories import ExecutionRepository
from app.domains.execution.schemas import (
    Operation,
    OperationCreate,
    OperationStatus,
    Task,
    TaskCreate,
    TaskDetail,
    TaskStatus,
    TaskType,
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
            task_status=TaskStatus.PENDING,
            task_type=TaskType.UNCLASSIFIED,
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
        if task.task_status not in {TaskStatus.PENDING, TaskStatus.PLANNING}:
            raise InvalidStateTransitionError(
                "Không thể thêm operation khi Task đang ở trạng thái "
                f"{task.task_status}"
            )
        operation = Operation(
            id=generate_id("oper"),
            task_id=task_id,
            **payload.model_dump(),
            operation_status=OperationStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        self._repository.save_operation(operation)
        if task.task_status == TaskStatus.PENDING:
            self._repository.save_task(
                task.model_copy(
                    update={
                        "task_status": TaskStatus.PLANNING,
                        "started_at": datetime.now(UTC),
                    }
                )
            )
        return operation

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
