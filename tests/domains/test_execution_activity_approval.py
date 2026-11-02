"""Unit tests cho timeline và quyết định phê duyệt của Execution domain."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    ApprovalDecision,
    ApprovalStatus,
    Operation,
    OperationDeviceApproval,
    OperationStatus,
    RiskLevel,
    Task,
    TaskActivityEvent,
    TaskStatus,
    TaskType,
)
from app.domains.execution.services import ExecutionService


class ApprovalRepositoryStub:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.task = Task(
            id="task-test",
            conversation_id="cons-test",
            source_message_id="mesg-test",
            user_id="user-owner",
            input_message="Cấu hình interface",
            task_status=TaskStatus.RUNNING,
            task_type=TaskType.CONFIGURATION,
            created_at=now,
        )
        self.operation = Operation(
            id="oper-test",
            task_id=self.task.id,
            operation_intent="CONFIGURE_INTERFACE",
            display_order=1,
            operation_status=OperationStatus.WAITING_APPROVAL,
            operation_parameters={},
            created_at=now,
        )
        self.event = TaskActivityEvent(
            id="actv-test",
            task_id=self.task.id,
            actor_type=ActivityActorType.PLANNER,
            event_type=ActivityEventType.PLAN_GENERATED,
            event_status=ActivityEventStatus.SUCCESS,
            sequence_number=1,
            created_at=now,
        )
        self.approval = OperationDeviceApproval(
            id="aprv-test",
            operation_device_id="opdv-test",
            approval_status=ApprovalStatus.PENDING,
            risk_level=RiskLevel.HIGH,
            requested_by="ORCHESTRATOR",
            reason="Thay đổi cấu hình thiết bị",
            commands_snapshot=["interface Ethernet0/0", "no shutdown"],
            request_hash="must-not-leak",
            requested_at=now,
            expires_at=now + timedelta(minutes=10),
            created_at=now,
        )
        self.expired_ids: list[str] = []

    def get_task_by_id(self, task_id: str):
        return self.task if task_id == self.task.id else None

    def get_operation_by_id(self, operation_id: str):
        return self.operation if operation_id == self.operation.id else None

    def get_all_task_activity_events_by_task_id(self, task_id: str):
        return [self.event] if task_id == self.task.id else []

    def get_all_operation_approvals_by_operation_id(self, operation_id: str):
        return [self.approval] if operation_id == self.operation.id else []

    def get_operation_approval_by_id(self, approval_id: str):
        return self.approval if approval_id == self.approval.id else None

    def expire_operation_approval(self, approval_id: str) -> None:
        self.expired_ids.append(approval_id)
        self.approval = self.approval.model_copy(
            update={"approval_status": ApprovalStatus.EXPIRED}
        )

    def decide_operation_approval(
        self,
        approval_id: str,
        user_id: str,
        decision: ApprovalDecision,
        decided_at: datetime,
    ):
        if approval_id != self.approval.id:
            return None
        self.approval = self.approval.model_copy(
            update={
                "approval_status": ApprovalStatus(decision.value),
                "decided_by": user_id,
                "decided_at": decided_at,
            }
        )
        return self.approval


def test_lists_activity_and_safe_approval_response() -> None:
    repository = ApprovalRepositoryStub()
    service = ExecutionService(repository)

    assert service.list_task_activity_events("task-test") == [repository.event]
    response = service.list_operation_approvals("oper-test")[0]

    assert response.id == "aprv-test"
    assert response.operation_device_id == "opdv-test"
    assert response.approval_status == ApprovalStatus.PENDING
    assert response.commands_snapshot == ["interface Ethernet0/0", "no shutdown"]
    assert response.reason == "Thay đổi cấu hình thiết bị"
    assert response.requested_at == repository.approval.requested_at
    assert "request_hash" not in response.model_dump()


class TaskRecordsRepositoryStub(ApprovalRepositoryStub):
    """Read-only repository stub for the Group 3 Task records endpoint."""

    def get_all_operations_by_task_id(self, task_id: str):
        return [self.operation] if task_id == self.task.id else []

    def get_all_operation_devices_by_operation_id(self, operation_id: str):
        return []

    def get_all_dependencies_by_operation_id(self, operation_id: str):
        return []

    def get_all_task_executions_by_task_id(self, task_id: str):
        return []

    def get_all_device_action_logs_by_task_id(self, task_id: str):
        return []


def test_task_records_include_operation_timeline_and_safe_approvals() -> None:
    repository = TaskRecordsRepositoryStub()
    service = ExecutionService(repository)

    records = service.get_task_records(repository.task.id)

    assert records.task.id == repository.task.id
    assert [operation.id for operation in records.task.operations] == [
        repository.operation.id
    ]
    assert records.activity_events[0].actor_type == ActivityActorType.PLANNER
    assert records.approvals[0].approval_status == ApprovalStatus.PENDING
    assert records.approvals[0].commands_snapshot == [
        "interface Ethernet0/0", "no shutdown"
    ]
    assert "request_hash" not in records.model_dump_json()
    assert records.operation_devices == []
    assert records.dependencies == []
    assert records.executions == []


def test_task_scoped_logs_require_valid_task() -> None:
    service = ExecutionService(TaskRecordsRepositoryStub())

    assert service.list_device_action_logs_by_task("task-test") == []
    with pytest.raises(ResourceNotFoundError):
        service.list_device_action_logs_by_task("task-missing")
    with pytest.raises(ResourceNotFoundError):
        service.get_task_records("task-missing")


def test_approval_decision_uses_authenticated_user_and_is_final() -> None:
    repository = ApprovalRepositoryStub()
    service = ExecutionService(repository)

    response = service.decide_operation_approval(
        "aprv-test",
        user_id="user-reviewer",
        decision=ApprovalDecision.APPROVED,
    )

    assert response.approval_status == ApprovalStatus.APPROVED
    assert response.decided_by == "user-reviewer"
    assert response.decided_at is not None

    with pytest.raises(ResourceConflictError):
        service.decide_operation_approval(
            "aprv-test",
            user_id="user-reviewer",
            decision=ApprovalDecision.REJECTED,
        )


def test_expired_approval_cannot_be_decided() -> None:
    repository = ApprovalRepositoryStub()
    repository.approval = repository.approval.model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(seconds=1)}
    )
    service = ExecutionService(repository)

    with pytest.raises(ResourceConflictError, match="đã hết hạn"):
        service.decide_operation_approval(
            "aprv-test",
            user_id="user-reviewer",
            decision=ApprovalDecision.APPROVED,
        )

    assert repository.expired_ids == ["aprv-test"]
    assert repository.approval.approval_status == ApprovalStatus.EXPIRED


def test_missing_parent_resources_return_not_found() -> None:
    service = ExecutionService(ApprovalRepositoryStub())

    with pytest.raises(ResourceNotFoundError):
        service.list_task_activity_events("task-missing")
    with pytest.raises(ResourceNotFoundError):
        service.list_operation_approvals("oper-missing")
    with pytest.raises(ResourceNotFoundError):
        service.decide_operation_approval(
            "aprv-missing",
            user_id="user-reviewer",
            decision=ApprovalDecision.APPROVED,
        )


def test_new_approval_has_default_configured_deadline() -> None:
    from app.domains.execution.schemas import DeviceRole, AccessMode, TaskOperationDevice
    from app.domains.execution.utils import build_operation_device_approval

    now = datetime.now(UTC)
    operation = ApprovalRepositoryStub().operation
    mapping = TaskOperationDevice(
        id="opdv-test",
        operation_id=operation.id,
        device_id="devc-test",
        operation_device_status="WAITING_APPROVAL",
        device_role=DeviceRole.TARGET,
        access_mode=AccessMode.WRITE,
    )
    approval = build_operation_device_approval(
        operation,
        mapping,
        commands=["no shutdown"],
        request_hash="sha256-digest",
        requested_at=now,
        timeout_minutes=15,
    )
    assert approval.expires_at == now + timedelta(minutes=15)
    assert approval.approval_status == ApprovalStatus.PENDING


def test_old_pending_approval_with_null_deadline_still_expires() -> None:
    repository = ApprovalRepositoryStub()
    repository.approval = repository.approval.model_copy(
        update={
            "requested_at": datetime.now(UTC) - timedelta(minutes=20),
            "expires_at": None,
        }
    )
    service = ExecutionService(repository)

    with pytest.raises(ResourceConflictError, match="đã hết hạn"):
        service.decide_operation_approval(
            repository.approval.id,
            user_id="user-reviewer",
            decision=ApprovalDecision.APPROVED,
        )

    assert repository.approval.approval_status == ApprovalStatus.EXPIRED


def test_timeout_sweep_delegates_to_repository() -> None:
    repository = ApprovalRepositoryStub()
    called = []
    def expire_due_approvals(now, timeout_minutes):
        called.append((now, timeout_minutes))
        return ["task-test"]
    repository.expire_due_approvals = expire_due_approvals

    service = ExecutionService(repository)
    now = datetime.now(UTC)
    assert service.expire_due_approvals(now) == ["task-test"]
    assert called == [(now, 15)]
