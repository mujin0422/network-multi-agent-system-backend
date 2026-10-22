"""Repository cho bảng operation_device_approvals."""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select, update

from app.core.database import create_session_factory
from app.domains.execution.models import (
    OperationDeviceApprovalModel,
    TaskOperationDeviceModel,
)
from app.domains.execution.schemas import (
    ApprovalDecision,
    ApprovalStatus,
    OperationDeviceApproval,
    OperationDeviceStatus,
)


class OperationDeviceApprovalRepositoryProtocol(Protocol):
    def save_operation_device_approval(
        self,
        approval: OperationDeviceApproval,
    ) -> None: ...

    def list_operation_approvals(
        self,
        operation_id: str,
    ) -> list[OperationDeviceApproval]: ...

    def get_operation_approval(
        self,
        approval_id: str,
    ) -> OperationDeviceApproval | None: ...

    def get_operation_device_approval(
        self,
        operation_device_id: str,
    ) -> OperationDeviceApproval | None: ...

    def expire_operation_approval(self, approval_id: str) -> None: ...

    def decide_operation_approval(
        self,
        approval_id: str,
        user_id: str,
        decision: ApprovalDecision,
        decided_at: datetime,
    ) -> OperationDeviceApproval | None: ...


class OperationDeviceApprovalRepository:
    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def save_operation_device_approval(
        self,
        approval: OperationDeviceApproval,
    ) -> None:
        """Tạo approval duy nhất cho một operation-device WRITE."""

        with self._sessions.begin() as session:
            session.add(OperationDeviceApprovalModel(**approval.model_dump()))

    def list_operation_approvals(
        self,
        operation_id: str,
    ) -> list[OperationDeviceApproval]:
        """Lấy Approval của các Device mapping thuộc một Operation."""

        statement = (
            select(OperationDeviceApprovalModel)
            .join(
                TaskOperationDeviceModel,
                TaskOperationDeviceModel.id
                == OperationDeviceApprovalModel.operation_device_id,
            )
            .where(TaskOperationDeviceModel.operation_id == operation_id)
            .order_by(
                OperationDeviceApprovalModel.requested_at,
                OperationDeviceApprovalModel.id,
            )
        )
        with self._sessions() as session:
            return [
                OperationDeviceApproval.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]

    def get_operation_approval(
        self,
        approval_id: str,
    ) -> OperationDeviceApproval | None:
        with self._sessions() as session:
            model = session.get(OperationDeviceApprovalModel, approval_id)
            return (
                OperationDeviceApproval.model_validate(model, from_attributes=True)
                if model
                else None
            )

    def get_operation_device_approval(
        self,
        operation_device_id: str,
    ) -> OperationDeviceApproval | None:
        """Lấy Approval duy nhất của một operation-device mapping."""

        statement = select(OperationDeviceApprovalModel).where(
            OperationDeviceApprovalModel.operation_device_id == operation_device_id
        )
        with self._sessions() as session:
            model = session.scalar(statement)
            return (
                OperationDeviceApproval.model_validate(model, from_attributes=True)
                if model
                else None
            )

    def expire_operation_approval(self, approval_id: str) -> None:
        """Chuyển PENDING quá hạn thành EXPIRED theo cách idempotent."""

        with self._sessions.begin() as session:
            session.execute(
                update(OperationDeviceApprovalModel)
                .where(
                    OperationDeviceApprovalModel.id == approval_id,
                    OperationDeviceApprovalModel.approval_status
                    == ApprovalStatus.PENDING,
                )
                .values(approval_status=ApprovalStatus.EXPIRED)
            )

    def decide_operation_approval(
        self,
        approval_id: str,
        user_id: str,
        decision: ApprovalDecision,
        decided_at: datetime,
    ) -> OperationDeviceApproval | None:
        """Chốt Approval và mapping REJECTED trong cùng transaction."""

        with self._sessions.begin() as session:
            approval_model = session.scalar(
                select(OperationDeviceApprovalModel)
                .where(OperationDeviceApprovalModel.id == approval_id)
                .with_for_update()
            )
            if approval_model is None:
                return None
            if approval_model.approval_status != ApprovalStatus.PENDING:
                return None
            if (
                approval_model.expires_at is not None
                and approval_model.expires_at <= decided_at
            ):
                approval_model.approval_status = ApprovalStatus.EXPIRED
                return None

            approval_model.approval_status = ApprovalStatus(decision.value)
            approval_model.decided_by = user_id
            approval_model.decided_at = decided_at

            if decision == ApprovalDecision.REJECTED:
                mapping = session.get(
                    TaskOperationDeviceModel,
                    approval_model.operation_device_id,
                )
                if mapping is not None:
                    mapping.operation_device_status = OperationDeviceStatus.REJECTED
                    mapping.completed_at = decided_at

            session.flush()
            return OperationDeviceApproval.model_validate(
                approval_model,
                from_attributes=True,
            )
