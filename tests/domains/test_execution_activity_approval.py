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

    def get_task(self, task_id: str):
        return self.task if task_id == self.task.id else None

    def get_operation(self, operation_id: str):
        return self.operation if operation_id == self.operation.id else None

    def list_task_activity_events(self, task_id: str):
        return [self.event] if task_id == self.task.id else []

    def list_operation_approvals(self, operation_id: str):
        return [self.approval] if operation_id == self.operation.id else []

    def get_operation_approval(self, approval_id: str):
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
    assert "request_hash" not in response.model_dump()


def test_approval_decision_uses_authenticated_user_and_is_final() -> None:
    repository = ApprovalRepositoryStub()
    service = ExecutionService(repository)

    response = service.decide_operation_approval(
        "aprv-test",
        "user-reviewer",
        ApprovalDecision.APPROVED,
    )

    assert response.approval_status == ApprovalStatus.APPROVED
    assert response.decided_by == "user-reviewer"
    assert response.decided_at is not None

    with pytest.raises(ResourceConflictError):
        service.decide_operation_approval(
            "aprv-test",
            "user-reviewer",
            ApprovalDecision.REJECTED,
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
            "user-reviewer",
            ApprovalDecision.APPROVED,
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
            "user-reviewer",
            ApprovalDecision.APPROVED,
        )
