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
    ApprovalDecision,
    ApprovalStatus,
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    DeviceActionLog,
    ExecutionPlanCreate,
    Operation,
    OperationCreate,
    OperationDependency,
    OperationDeviceApproval,
    OperationDeviceApprovalResponse,
    OperationDeviceStatus,
    OperationStatus,
    RiskLevel,
    Task,
    TaskActivityEvent,
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

    # =============================================================================
    # Task — tạo và lấy yêu cầu xử lý
    # =============================================================================

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

    # =============================================================================
    # Operation, Device và Dependency — đọc kế hoạch thực thi
    # =============================================================================

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

    def get_operation_device(
        self,
        operation_device_id: str,
    ) -> TaskOperationDevice:
        """Lấy mapping hoặc báo lỗi để Orchestrator có thể resume Task."""

        mapping = self._repository.get_operation_device(operation_device_id)
        if mapping is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy Task Operation Device '{operation_device_id}'"
            )
        return mapping

    def list_dependencies(self, operation_id: str) -> list[OperationDependency]:
        self._require_operation(operation_id)
        return self._repository.list_dependencies(operation_id)

    # =============================================================================
    # Task Activity Event — lấy và ghi timeline của các agent
    # =============================================================================

    def list_task_activity_events(self, task_id: str) -> list[TaskActivityEvent]:
        """Lấy timeline của Task sau khi xác nhận Task tồn tại."""

        self._require_task(task_id)
        return self._repository.list_task_activity_events(task_id)

    def record_activity(
        self,
        task_id: str,
        actor_type: ActivityActorType,
        event_type: ActivityEventType,
        event_status: ActivityEventStatus = ActivityEventStatus.SUCCESS,
        *,
        operation_id: str | None = None,
        execution_id: str | None = None,
        event_data: dict | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> TaskActivityEvent:
        """Nối một event có thứ tự vào timeline của Task."""

        self._require_task(task_id)
        now = datetime.now(UTC)
        events = self._repository.list_task_activity_events(task_id)
        if started_at is None:
            started_at = now
        if completed_at is None and event_status in {
            ActivityEventStatus.SUCCESS,
            ActivityEventStatus.FAILED,
            ActivityEventStatus.SKIPPED,
        }:
            completed_at = now
        event = TaskActivityEvent(
            id=generate_id(IdPrefix.TASK_ACTIVITY),
            task_id=task_id,
            operation_id=operation_id,
            execution_id=execution_id,
            actor_type=actor_type,
            event_type=event_type,
            event_status=event_status,
            sequence_number=max((item.sequence_number for item in events), default=0) + 1,
            event_data=event_data or {},
            started_at=started_at,
            completed_at=completed_at,
            created_at=now,
        )
        self._repository.save_task_activity_event(event)
        return event

    # =============================================================================
    # Operation Device Approval — yêu cầu và quyết định phê duyệt
    # =============================================================================

    def list_operation_approvals(
        self,
        operation_id: str,
    ) -> list[OperationDeviceApprovalResponse]:
        """Lấy các yêu cầu phê duyệt mà không làm lộ request_hash."""

        self._require_operation(operation_id)
        return [
            self._to_approval_response(approval)
            for approval in self._repository.list_operation_approvals(operation_id)
        ]

    def get_operation_device_approval(
        self,
        operation_device_id: str,
    ) -> OperationDeviceApproval | None:
        """Lấy Approval nội bộ để Orchestrator kiểm tra trước khi WRITE."""

        return self._repository.get_operation_device_approval(operation_device_id)

    def create_operation_device_approval(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        commands: list[str],
        request_hash: str,
    ) -> OperationDeviceApproval:
        """Tạo snapshot PENDING trước khi cho phép thực thi lệnh WRITE."""

        existing = self._repository.get_operation_device_approval(mapping.id)
        if existing is not None:
            return existing

        now = datetime.now(UTC)
        approval = OperationDeviceApproval(
            id=generate_id(IdPrefix.OPERATION_DEVICE_APPROVAL),
            operation_device_id=mapping.id,
            approval_status=ApprovalStatus.PENDING,
            risk_level=RiskLevel.HIGH,
            requested_by="execution-orchestrator",
            reason=(
                f"Operation {operation.operation_intent} sẽ thay đổi cấu hình "
                f"trên thiết bị {mapping.device_id}."
            ),
            commands_snapshot=commands,
            request_hash=request_hash,
            requested_at=now,
            created_at=now,
        )
        self._repository.save_operation_device_approval(approval)
        return approval

    def expire_operation_approval(self, approval_id: str) -> None:
        """Đánh dấu Approval PENDING đã quá hạn."""

        self._repository.expire_operation_approval(approval_id)

    def decide_operation_approval(
        self,
        approval_id: str,
        user_id: str,
        decision: ApprovalDecision,
    ) -> OperationDeviceApprovalResponse:
        """Chốt một Approval đúng một lần bằng danh tính từ access token."""

        approval = self._repository.get_operation_approval(approval_id)
        if approval is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy Operation Device Approval '{approval_id}'"
            )
        if approval.approval_status != ApprovalStatus.PENDING:
            raise ResourceConflictError(
                f"Approval '{approval_id}' đã được xử lý hoặc hết hạn"
            )

        now = datetime.now(UTC)
        if approval.expires_at is not None and approval.expires_at <= now:
            self._repository.expire_operation_approval(approval_id)
            raise ResourceConflictError(f"Approval '{approval_id}' đã hết hạn")

        decided = self._repository.decide_operation_approval(
            approval_id,
            user_id,
            decision,
            now,
        )
        if decided is None:
            # Repository khóa bản ghi khi cập nhật. None tại đây nghĩa là một
            # request đồng thời đã chốt Approval hoặc thời hạn vừa kết thúc.
            current = self._repository.get_operation_approval(approval_id)
            if current is not None and current.approval_status == ApprovalStatus.EXPIRED:
                raise ResourceConflictError(f"Approval '{approval_id}' đã hết hạn")
            raise ResourceConflictError(f"Approval '{approval_id}' đã được xử lý")
        return self._to_approval_response(decided)

    # =============================================================================
    # Task, Operation và Device — cập nhật trạng thái thực thi
    # =============================================================================

    def update_task(self, task: Task) -> None:
        self._repository.save_task(task)

    def update_operation(self, operation: Operation) -> None:
        self._repository.save_operation(operation)

    def update_operation_device(self, mapping: TaskOperationDevice) -> None:
        self._repository.save_operation_device(mapping)

    # =============================================================================
    # Task Execution và Device Action Log — lưu kết quả và nhật ký lệnh
    # =============================================================================

    def save_task_execution(self, execution: TaskExecution) -> None:
        self._repository.save_task_execution(execution)

    def save_device_action_logs(self, logs: list[DeviceActionLog]) -> None:
        self._repository.save_device_action_logs(logs)

    # =============================================================================
    # Execution Plan — tạo operation và lưu kế hoạch nguyên tử
    # =============================================================================

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

    # =============================================================================
    # Xác minh tài nguyên và chuyển đổi response
    # =============================================================================

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

    @staticmethod
    def _to_approval_response(
        approval: OperationDeviceApproval,
    ) -> OperationDeviceApprovalResponse:
        return OperationDeviceApprovalResponse.model_validate(
            approval.model_dump(exclude={"request_hash"})
        )
