"""Public service cho vòng đời Task và Operation."""

from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.domains.audit.transaction import audit_mutation

from app.core.exceptions import (
    InvalidStateTransitionError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.core.utils import IdPrefix, generate_id
from app.domains.execution.repositories import ExecutionRepository
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
    OperationStatus,
    Task,
    TaskActivityEvent,
    TaskCreate,
    TaskDetail,
    TaskRecords,
    TaskStatus,
    TaskOperationDevice,
    TaskExecution,
    TaskType,
)
from app.domains.execution.utils import (
    build_execution_plan_records,
    build_operation_device_approval,
    to_approval_response,
)


class ExecutionService:
    def __init__(self, repository: ExecutionRepository) -> None:
        self._repository = repository

    # =============================================================================
    # Task — tạo và lấy yêu cầu xử lý
    # =============================================================================

    def create_task(self, payload: TaskCreate) -> Task:
        # source_message_id là UNIQUE: một message người dùng chỉ sinh một Task.
        if self._repository.get_task_by_source_message_id(payload.source_message_id):
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
        with audit_mutation("TASK_CREATE", "TASK", task.id, actor_user_id=task.user_id):
            self._repository.save_task(task)
        return task

    def list_tasks(self) -> list[Task]:
        return self._repository.get_all_tasks()

    def get_task(self, task_id: str) -> TaskDetail:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_task."""
        task = self._require_task(task_id)
        return TaskDetail(
            **task.model_dump(),
            operations=self._repository.get_all_operations_by_task_id(task_id),
        )

    def get_task_records(self, task_id: str) -> TaskRecords:
        """Đọc các bản ghi GROUP 3 của Task; không trả command logs ở đây."""

        task = self.get_task(task_id)
        operation_ids = [operation.id for operation in task.operations]
        return TaskRecords(
            task=task,
            operation_devices=[
                mapping
                for operation_id in operation_ids
                for mapping in self._repository.get_all_operation_devices_by_operation_id(
                    operation_id
                )
            ],
            dependencies=[
                dependency
                for operation_id in operation_ids
                for dependency in self._repository.get_all_dependencies_by_operation_id(
                    operation_id
                )
            ],
            executions=self._repository.get_all_task_executions_by_task_id(task_id),
            activity_events=self._repository.get_all_task_activity_events_by_task_id(task_id),
            approvals=[
                to_approval_response(approval)
                for operation_id in operation_ids
                for approval in self._repository.get_all_operation_approvals_by_operation_id(
                    operation_id
                )
            ],
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
        return self._repository.get_all_operation_devices_by_operation_id(
            operation_id
        )

    def get_operation_device(
        self,
        operation_device_id: str,
    ) -> TaskOperationDevice:
        """Lấy mapping hoặc báo lỗi để Orchestrator có thể resume Task."""

        mapping = self._repository.get_operation_device_by_id(operation_device_id)
        if mapping is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy Task Operation Device '{operation_device_id}'"
            )
        return mapping

    def list_dependencies(self, operation_id: str) -> list[OperationDependency]:
        """Truy vấn danh sách dữ liệu theo phạm vi của phương thức list_dependencies."""
        self._require_operation(operation_id)
        return self._repository.get_all_dependencies_by_operation_id(operation_id)

    # =============================================================================
    # Task Activity Event — lấy và ghi timeline của các agent
    # =============================================================================

    def list_task_activity_events(self, task_id: str) -> list[TaskActivityEvent]:
        """Lấy timeline của Task sau khi xác nhận Task tồn tại."""

        self._require_task(task_id)
        return self._repository.get_all_task_activity_events_by_task_id(task_id)

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
        events = self._repository.get_all_task_activity_events_by_task_id(task_id)
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
            to_approval_response(approval)
            for approval in self._repository.get_all_operation_approvals_by_operation_id(
                operation_id
            )
        ]

    def get_operation_device_approval(
        self,
        operation_device_id: str,
    ) -> OperationDeviceApproval | None:
        """Lấy Approval nội bộ để Orchestrator kiểm tra trước khi WRITE."""

        return self._repository.get_approval_by_operation_device_id(
            operation_device_id
        )

    def create_operation_device_approval(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        *,
        commands: list[str],
        request_hash: str,
    ) -> OperationDeviceApproval:
        """Tạo snapshot PENDING trước khi cho phép thực thi lệnh WRITE."""

        existing = self._repository.get_approval_by_operation_device_id(mapping.id)
        if existing is not None:
            return existing

        approval = build_operation_device_approval(
            operation,
            mapping,
            commands,
            request_hash,
            datetime.now(UTC),
            timeout_minutes=get_settings().approval_timeout_minutes,
        )
        self._repository.save_operation_device_approval(approval)
        return approval

    def expire_due_approvals(self, now: datetime | None = None) -> list[str]:
        """Atomically finalize overdue approvals, their Tasks and Benchmark Runs."""

        return self._repository.expire_due_approvals(
            now or datetime.now(UTC),
            get_settings().approval_timeout_minutes,
        )

    def expire_operation_approval(self, approval_id: str) -> None:
        """Đánh dấu Approval PENDING đã quá hạn."""

        self._repository.expire_operation_approval(approval_id)

    def decide_operation_approval(
        self,
        approval_id: str,
        *,
        user_id: str,
        decision: ApprovalDecision,
    ) -> OperationDeviceApprovalResponse:
        """Chốt một Approval đúng một lần bằng danh tính từ access token."""

        approval = self._repository.get_operation_approval_by_id(approval_id)
        if approval is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy Operation Device Approval '{approval_id}'"
            )
        if approval.approval_status != ApprovalStatus.PENDING:
            raise ResourceConflictError(
                f"Approval '{approval_id}' đã được xử lý hoặc hết hạn"
            )

        now = datetime.now(UTC)
        # Legacy rows may have NULL expires_at. Still apply the configured TTL.
        deadline = approval.expires_at or (
            approval.requested_at
            + timedelta(minutes=get_settings().approval_timeout_minutes)
        )
        if deadline <= now:
            self._repository.expire_operation_approval(approval_id)
            raise ResourceConflictError(f"Approval '{approval_id}' đã hết hạn")

        with audit_mutation(
            "APPROVAL_APPROVE" if decision == ApprovalDecision.APPROVED else "APPROVAL_REJECT",
            "APPROVAL", approval_id, actor_user_id=user_id,
        ):
            decided = self._repository.decide_operation_approval(
                approval_id,
                user_id=user_id,
                decision=decision,
                decided_at=now,
            )
        if decided is None:
            # Repository khóa bản ghi khi cập nhật. None tại đây nghĩa là một
            # request đồng thời đã chốt Approval hoặc thời hạn vừa kết thúc.
            current = self._repository.get_operation_approval_by_id(approval_id)
            if current is not None and current.approval_status == ApprovalStatus.EXPIRED:
                raise ResourceConflictError(f"Approval '{approval_id}' đã hết hạn")
            raise ResourceConflictError(f"Approval '{approval_id}' đã được xử lý")
        return to_approval_response(decided)

    # =============================================================================
    # Task, Operation và Device — cập nhật trạng thái thực thi
    # =============================================================================

    def update_task(self, task: Task) -> None:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức update_task."""
        self._repository.save_task(task)

    def update_operation(self, operation: Operation) -> None:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức update_operation."""
        self._repository.save_operation(operation)

    def update_operation_device(self, mapping: TaskOperationDevice) -> None:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức update_operation_device."""
        self._repository.save_operation_device(mapping)

    # =============================================================================
    # Task Execution và Device Action Log — lưu kết quả và nhật ký lệnh
    # =============================================================================

    def save_task_execution(self, execution: TaskExecution) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_task_execution."""
        self._repository.save_task_execution(execution)

    def save_device_action_logs(self, logs: list[DeviceActionLog]) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_device_action_logs."""
        self._repository.save_device_action_logs(logs)

    def list_device_action_logs(self, limit: int = 500) -> list[DeviceActionLog]:
        return self._repository.get_recent_device_action_logs(limit)

    def list_device_action_logs_by_task(self, task_id: str) -> list[DeviceActionLog]:
        self._require_task(task_id)
        return self._repository.get_all_device_action_logs_by_task_id(task_id)

    # =============================================================================
    # Execution Plan — tạo operation và lưu kế hoạch nguyên tử
    # =============================================================================

    def create_operation(self, task_id: str, payload: OperationCreate) -> Operation:
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
        with audit_mutation("OPERATION_CREATE", "OPERATION", operation.id):
            updated_task = (
            task.model_copy(
                update={
                    "task_status": TaskStatus.PLANNING,
                    "started_at": datetime.now(UTC),
                }
            )
            if task.task_status == TaskStatus.PENDING
            else None
        )
        with audit_mutation("OPERATION_CREATE", "OPERATION", operation.id):
            atomic_create = getattr(self._repository, "create_operation_atomic", None)
            if atomic_create is not None:
                atomic_create(operation, updated_task)
            else:
                # Compatibility for existing in-memory test repositories.
                self._repository.save_operation(operation)
                if updated_task is not None:
                    self._repository.save_task(updated_task)
        return operation

    def create_execution_plan(
        self,
        task_id: str,
        plan: ExecutionPlanCreate,
    ) -> TaskDetail:
        """Chuyển structured plan thành các record và lưu nguyên tử."""

        task = self._require_task(task_id)
        if self._repository.get_all_operations_by_task_id(task_id):
            raise ResourceConflictError(f"Task '{task_id}' đã có execution plan")
        if task.task_status != TaskStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Task '{task_id}' không còn ở trạng thái PENDING"
            )

        records = build_execution_plan_records(task, plan, datetime.now(UTC))
        self._repository.save_execution_plan(
            records.task,
            operations=records.operations,
            dependencies=records.dependencies,
            operation_devices=records.operation_devices,
        )
        return self.get_task(task_id)

    # =============================================================================
    # Xác minh tài nguyên và chuyển đổi response
    # =============================================================================

    def _require_task(self, task_id: str) -> Task:
        task = self._repository.get_task_by_id(task_id)
        if task is None:
            raise ResourceNotFoundError(f"Không tìm thấy Task '{task_id}'")
        return task

    def _require_operation(self, operation_id: str) -> Operation:
        operation = self._repository.get_operation_by_id(operation_id)
        if operation is None:
            raise ResourceNotFoundError(f"Không tìm thấy Operation '{operation_id}'")
        return operation
