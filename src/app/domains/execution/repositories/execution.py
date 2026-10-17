"""Persistence contract và adapter in-memory của Execution domain."""

from typing import Protocol

from app.domains.execution.schemas import Operation, Task


class ExecutionRepository(Protocol):
    def save_task(self, task: Task) -> None: ...

    def get_task(self, task_id: str) -> Task | None: ...

    def list_tasks(self) -> list[Task]: ...

    def find_task_by_source_message(self, message_id: str) -> Task | None: ...

    def save_operation(self, operation: Operation) -> None: ...

    def get_operation(self, operation_id: str) -> Operation | None: ...

    def list_operations(self, task_id: str) -> list[Operation]: ...


class InMemoryExecutionRepository:
    """Kho dữ liệu thử nghiệm giữ cùng contract với SQL repository tương lai."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._operations: dict[str, Operation] = {}

    def save_task(self, task: Task) -> None:
        self._tasks[task.id] = task.model_copy(deep=True)

    def get_task(self, task_id: str) -> Task | None:
        task = self._tasks.get(task_id)
        return task.model_copy(deep=True) if task else None

    def list_tasks(self) -> list[Task]:
        return [item.model_copy(deep=True) for item in self._tasks.values()]

    def find_task_by_source_message(self, message_id: str) -> Task | None:
        return next(
            (
                task.model_copy(deep=True)
                for task in self._tasks.values()
                if task.source_message_id == message_id
            ),
            None,
        )

    def save_operation(self, operation: Operation) -> None:
        self._operations[operation.id] = operation.model_copy(deep=True)

    def get_operation(self, operation_id: str) -> Operation | None:
        operation = self._operations.get(operation_id)
        return operation.model_copy(deep=True) if operation else None

    def list_operations(self, task_id: str) -> list[Operation]:
        operations = [
            item.model_copy(deep=True)
            for item in self._operations.values()
            if item.task_id == task_id
        ]
        return sorted(operations, key=lambda item: item.display_order)
