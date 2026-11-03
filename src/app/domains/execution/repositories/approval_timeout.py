"""Atomic expiry of human approvals and all dependent execution state.

The SELECT FOR UPDATE / SKIP LOCKED strategy lets several API workers run
the sweep without finalizing the same task twice. All updates, including an
associated benchmark run, commit together.
"""

from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select

from app.core.database import create_session_factory
from app.core.utils import IdPrefix, generate_id, generate_uuid
from app.domains.audit.models import AuditLogModel
from app.domains.audit.schemas import AuditActorType, AuditEventStatus
from app.domains.benchmark.models import BenchmarkRunModel
from app.domains.execution.models import (
    OperationDeviceApprovalModel,
    OperationModel,
    TaskActivityEventModel,
    TaskModel,
    TaskOperationDeviceModel,
)
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    ApprovalStatus,
    OperationDeviceStatus,
    OperationStatus,
    TaskStatus,
)

_TERMINAL_TASKS = {
    TaskStatus.SUCCESS,
    TaskStatus.PARTIAL_SUCCESS,
    TaskStatus.FAILED,
    TaskStatus.REJECTED,
}
_TERMINAL_OPERATIONS = {
    OperationStatus.SUCCESS,
    OperationStatus.PARTIAL_SUCCESS,
    OperationStatus.FAILED,
    OperationStatus.REJECTED,
    OperationStatus.SKIPPED,
}
_TERMINAL_MAPPINGS = {
    OperationDeviceStatus.SUCCESS,
    OperationDeviceStatus.FAILED,
    OperationDeviceStatus.REJECTED,
    OperationDeviceStatus.SKIPPED,
}
_TIMEOUT_REASON = "APPROVAL_TIMEOUT"


class ApprovalTimeoutRepository:
    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def expire_due_approvals(
        self,
        now: datetime,
        timeout_minutes: int,
        limit: int = 100,
    ) -> list[str]:
        """Finalize overdue Tasks atomically, preserving completed operations.

        Legacy approvals with a NULL expires_at use requested_at + configured TTL.
        EXPIRED rows are also revisited to recover from a decision request that
        expired the approval before the periodic sweeper could finalize its Task.
        """
        cutoff = now - timedelta(minutes=timeout_minutes)
        due = or_(
            OperationDeviceApprovalModel.expires_at <= now,
            and_(
                OperationDeviceApprovalModel.expires_at.is_(None),
                OperationDeviceApprovalModel.requested_at <= cutoff,
            ),
        )
        finished: list[str] = []
        with self._sessions.begin() as session:
            candidates = session.scalars(
                select(OperationDeviceApprovalModel.id)
                .join(
                    TaskOperationDeviceModel,
                    TaskOperationDeviceModel.id
                    == OperationDeviceApprovalModel.operation_device_id,
                )
                .join(
                    OperationModel,
                    OperationModel.id == TaskOperationDeviceModel.operation_id,
                )
                .join(TaskModel, TaskModel.id == OperationModel.task_id)
                .where(
                    OperationDeviceApprovalModel.approval_status.in_(
                        (ApprovalStatus.PENDING, ApprovalStatus.EXPIRED)
                    ),
                    TaskModel.task_status.not_in(_TERMINAL_TASKS),
                    due,
                )
                .order_by(OperationDeviceApprovalModel.requested_at)
                .limit(limit)
            ).all()

            for approval_id in candidates:
                approval = session.scalar(
                    select(OperationDeviceApprovalModel)
                    .where(OperationDeviceApprovalModel.id == approval_id)
                    .with_for_update(skip_locked=True)
                )
                if approval is None or approval.approval_status not in (
                    ApprovalStatus.PENDING,
                    ApprovalStatus.EXPIRED,
                ):
                    continue
                effective_expiry = approval.expires_at or (
                    approval.requested_at + timedelta(minutes=timeout_minutes)
                )
                if effective_expiry > now:
                    continue

                mapping = session.get(
                    TaskOperationDeviceModel, approval.operation_device_id
                )
                if mapping is None:
                    continue
                operation = session.get(OperationModel, mapping.operation_id)
                if operation is None:
                    continue
                task = session.scalar(
                    select(TaskModel)
                    .where(TaskModel.id == operation.task_id)
                    .with_for_update(skip_locked=True)
                )
                if task is None or task.task_status in _TERMINAL_TASKS:
                    continue

                operations = session.scalars(
                    select(OperationModel)
                    .where(OperationModel.task_id == task.id)
                    .order_by(OperationModel.display_order)
                ).all()
                operation_ids = [item.id for item in operations]
                mappings = session.scalars(
                    select(TaskOperationDeviceModel).where(
                        TaskOperationDeviceModel.operation_id.in_(operation_ids)
                    )
                ).all()
                mapping_ids = [item.id for item in mappings]

                pending_approvals = session.scalars(
                    select(OperationDeviceApprovalModel)
                    .where(
                        OperationDeviceApprovalModel.operation_device_id.in_(mapping_ids),
                        OperationDeviceApprovalModel.approval_status
                        == ApprovalStatus.PENDING,
                    )
                    .with_for_update()
                ).all()
                for pending in pending_approvals:
                    pending.approval_status = ApprovalStatus.EXPIRED

                approved_ids = {item.operation_device_id for item in pending_approvals}
                approved_ids.add(approval.operation_device_id)
                for item in mappings:
                    if item.operation_device_status in _TERMINAL_MAPPINGS:
                        continue
                    is_unapproved_write = item.id in approved_ids
                    item.operation_device_status = (
                        OperationDeviceStatus.REJECTED
                        if is_unapproved_write
                        else OperationDeviceStatus.SKIPPED
                    )
                    item.error_message = (
                        "Approval timed out; WRITE was not executed"
                        if is_unapproved_write
                        else "Task stopped after approval timeout"
                    )
                    item.completed_at = now

                mappings_by_operation: dict[str, list[TaskOperationDeviceModel]] = {}
                for item in mappings:
                    mappings_by_operation.setdefault(item.operation_id, []).append(item)
                any_success = False
                for item in operations:
                    if item.operation_status in _TERMINAL_OPERATIONS:
                        if item.operation_status in (
                            OperationStatus.SUCCESS,
                            OperationStatus.PARTIAL_SUCCESS,
                        ):
                            any_success = True
                        continue
                    statuses = [
                        mapping.operation_device_status
                        for mapping in mappings_by_operation.get(item.id, [])
                    ]
                    if statuses and all(
                        status == OperationDeviceStatus.SUCCESS for status in statuses
                    ):
                        item.operation_status = OperationStatus.SUCCESS
                        any_success = True
                    elif OperationDeviceStatus.SUCCESS in statuses:
                        item.operation_status = OperationStatus.PARTIAL_SUCCESS
                        any_success = True
                    elif OperationDeviceStatus.REJECTED in statuses:
                        item.operation_status = OperationStatus.REJECTED
                    else:
                        item.operation_status = OperationStatus.SKIPPED
                    item.completed_at = now

                task.task_status = (
                    TaskStatus.PARTIAL_SUCCESS if any_success else TaskStatus.FAILED
                )
                task.completed_at = now

                next_seq = session.scalar(
                    select(func.coalesce(func.max(TaskActivityEventModel.sequence_number), 0))
                    .where(TaskActivityEventModel.task_id == task.id)
                ) + 1
                session.add(
                    TaskActivityEventModel(
                        id=generate_id(IdPrefix.TASK_ACTIVITY),
                        task_id=task.id,
                        actor_type=ActivityActorType.ORCHESTRATOR,
                        event_type=(
                            ActivityEventType.TASK_COMPLETED
                            if any_success
                            else ActivityEventType.TASK_FAILED
                        ),
                        event_status=(
                            ActivityEventStatus.SUCCESS
                            if any_success
                            else ActivityEventStatus.FAILED
                        ),
                        sequence_number=next_seq,
                        event_data={
                            "reason": _TIMEOUT_REASON,
                            "approval_id": approval.id,
                            "timeout_minutes": timeout_minutes,
                            "task_status": task.task_status.value,
                        },
                        started_at=now,
                        completed_at=now,
                        created_at=now,
                    )
                )

                # The system audit event commits with the Task status transition.
                session.add(
                    AuditLogModel(
                        id=generate_uuid(),
                        actor_user_id=None,
                        actor_display_name="Approval timeout worker",
                        actor_type=AuditActorType.SYSTEM,
                        action="APPROVAL_TIMEOUT",
                        resource_type="TASK",
                        resource_id=task.id,
                        event_status=AuditEventStatus.FAILED,
                        summary="Task ended because approval was not given before deadline",
                        event_data={
                            "approval_id": approval.id,
                            "timeout_minutes": timeout_minutes,
                            "task_status": task.task_status.value,
                        },
                        occurred_at=now,
                    )
                )

                # Keep the benchmark's cleanup flag intact; fault injection may
                # have changed the lab and must still be manually cleaned up.
                run = session.scalar(
                    select(BenchmarkRunModel)
                    .where(
                        BenchmarkRunModel.source_message_id == task.source_message_id,
                        BenchmarkRunModel.status == "RUNNING",
                    )
                    .with_for_update()
                )
                if run is not None:
                    run.status = "FAILED"
                    run.task_id = task.id
                    run.error_message = "APPROVAL_TIMEOUT: timed out waiting for approval"
                    run.completed_at = now

                finished.append(task.id)

        return finished
