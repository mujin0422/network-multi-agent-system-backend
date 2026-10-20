"""Public service cho vòng đời Task và Operation."""

from datetime import UTC, datetime

from app.core.exceptions import (
    InvalidStateTransitionError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.core.utils import IdPrefix, generate_id
from app.domains.execution.repositories import ExecutionRepositoryProtocol
from app.domains.execution.schemas import (
    Operation,
    OperationCreate,
    OperationDependency,
    OperationDeviceStatus,
    OperationStatus,
    DeviceActionLog,
    ExecutionPlanCreate,
    Task,
    TaskCreate,
    TaskDetail,
    TaskStatus,
    TaskOperationDevice,
    TaskExecution,
    TaskType,
)


class ExecutionService:
    def __init__(self, repository: ExecutionRepositoryProtocol) -> None:
        self._repository = repository

    def create_task(self, payload: TaskCreate) -> Task:
        # source_message_id là UNIQUE: một message người dùng chỉ sinh một Task.
        if self._repository.find_task_by_source_message(payload.source_message_id):
            raise ResourceConflictError(
                f"Message '{payload.source_message_id}' đã tạo Task trước đó"
            )
        task = Task(
            id=generate_id(IdPrefix.TASK),
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

    def get_operation(self, operation_id: str) -> Operation:
        """Lấy operation cho application-layer executor."""

        return self._require_operation(operation_id)

    def list_operation_devices(
        self,
        operation_id: str,
    ) -> list[TaskOperationDevice]:
        """Lấy các device mapping đã được Planner tạo cho operation."""

        self._require_operation(operation_id)
        return self._repository.list_operation_devices(operation_id)

    def list_dependencies(self, operation_id: str) -> list[OperationDependency]:
        self._require_operation(operation_id)
        return self._repository.list_dependencies(operation_id)

    def update_task(self, task: Task) -> None:
        self._repository.save_task(task)

    def update_operation(self, operation: Operation) -> None:
        self._repository.save_operation(operation)

    def update_operation_device(self, mapping: TaskOperationDevice) -> None:
        self._repository.save_operation_device(mapping)

    def save_task_execution(self, execution: TaskExecution) -> None:
        self._repository.save_task_execution(execution)

    def save_device_action_logs(self, logs: list[DeviceActionLog]) -> None:
        self._repository.save_device_action_logs(logs)

    def add_operation(self, task_id: str, payload: OperationCreate) -> Operation:
        task = self._require_task(task_id)
        if task.task_status not in {TaskStatus.PENDING, TaskStatus.PLANNING}:
            raise InvalidStateTransitionError(
                "Không thể thêm operation khi Task đang ở trạng thái "
                f"{task.task_status}"
            )
        operation = Operation(
            id=generate_id(IdPrefix.OPERATION),
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

    def create_execution_plan(
        self,
        task_id: str,
        plan: ExecutionPlanCreate,
    ) -> TaskDetail:
        """Chuyển structured plan thành các record và lưu nguyên tử."""

        task = self._require_task(task_id)
        if self._repository.list_operations(task_id):
            raise ResourceConflictError(f"Task '{task_id}' đã có execution plan")
        if task.task_status != TaskStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Task '{task_id}' không còn ở trạng thái PENDING"
            )

        now = datetime.now(UTC)
        operations: list[Operation] = []
        dependencies: list[OperationDependency] = []
        operation_devices: list[TaskOperationDevice] = []

        for display_order, planned_operation in enumerate(plan.operations, start=1):
            operation = Operation(
                id=generate_id(IdPrefix.OPERATION),
                task_id=task_id,
                operation_intent=planned_operation.operation_intent,
                display_order=display_order,
                operation_status=OperationStatus.PENDING,
                operation_parameters=planned_operation.operation_parameters,
                created_at=now,
            )
            operations.append(operation)

            for planned_dependency in planned_operation.dependencies:
                dependencies.append(
                    OperationDependency(
                        id=generate_id(IdPrefix.OPERATION_DEPENDENCY),
                        operation_id=operation.id,
                        depends_on_operation_id=operations[
                            planned_dependency.depends_on_order - 1
                        ].id,
                        dependency_type=planned_dependency.dependency_type,
                        created_at=now,
                    )
                )

            for planned_device in planned_operation.devices:
                operation_devices.append(
                    TaskOperationDevice(
                        id=generate_id(IdPrefix.OPERATION_DEVICE),
                        operation_id=operation.id,
                        device_id=planned_device.device_id,
                        operation_device_status=OperationDeviceStatus.PENDING,
                        device_role=planned_device.device_role,
                        access_mode=planned_device.access_mode,
                    )
                )

        planned_task = task.model_copy(
            update={
                "task_status": TaskStatus.PLANNING,
                "task_type": plan.task_type,
                "started_at": now,
            }
        )
        self._repository.save_execution_plan(
            planned_task,
            operations,
            dependencies,
            operation_devices,
        )
        return TaskDetail(**planned_task.model_dump(), operations=operations)

    def _require_task(self, task_id: str) -> Task:
        task = self._repository.get_task(task_id)
        if task is None:
            raise ResourceNotFoundError(f"Không tìm thấy Task '{task_id}'")
        return task

    def _require_operation(self, operation_id: str) -> Operation:
        operation = self._repository.get_operation(operation_id)
        if operation is None:
            raise ResourceNotFoundError(f"Không tìm thấy Operation '{operation_id}'")
        return operation
