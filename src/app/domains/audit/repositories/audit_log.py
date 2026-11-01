"""Persistence contract và SQLAlchemy repository cho audit_logs."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import Select, select

from app.core.database import create_session_factory
from app.domains.audit.models import AuditLogModel
from app.domains.audit.schemas import AuditEventStatus, AuditLog


class AuditLogRepositoryProtocol(Protocol):
    def add(self, audit_log: AuditLog) -> None:
        """Tạo mới dữ liệu theo nghiệp vụ của phương thức add."""
        ...

    def get_by_id(self, audit_log_id: UUID) -> AuditLog | None:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        ...

    def get_all(
        self,
        *,
        actor_user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        event_status: AuditEventStatus | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all."""
        ...


class AuditLogRepository:
    """Đọc và ghi append-only đối với bảng audit_logs."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo AuditLogRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    @staticmethod
    def _to_schema(model: AuditLogModel | None) -> AuditLog | None:
        """Chuyển đổi dữ liệu nội bộ trong phương thức _to_schema."""
        return (
            AuditLog.model_validate(model, from_attributes=True)
            if model is not None
            else None
        )

    def add(self, audit_log: AuditLog) -> None:
        """Chèn một bản ghi mới; repository không cung cấp update hoặc delete."""

        with self._sessions.begin() as session:
            session.add(AuditLogModel(**audit_log.model_dump()))

    def get_by_id(self, audit_log_id: UUID) -> AuditLog | None:
        """Lấy một audit log theo UUID."""

        with self._sessions() as session:
            return self._to_schema(session.get(AuditLogModel, audit_log_id))

    def get_all(
        self,
        *,
        actor_user_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        event_status: AuditEventStatus | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        """Lọc audit log và trả dữ liệu mới nhất trước."""

        statement: Select = select(AuditLogModel)
        if actor_user_id is not None:
            statement = statement.where(
                AuditLogModel.actor_user_id == actor_user_id
            )
        if action is not None:
            statement = statement.where(AuditLogModel.action == action.upper())
        if resource_type is not None:
            statement = statement.where(
                AuditLogModel.resource_type == resource_type.upper()
            )
        if event_status is not None:
            statement = statement.where(
                AuditLogModel.event_status == event_status
            )
        if occurred_from is not None:
            statement = statement.where(
                AuditLogModel.occurred_at >= occurred_from
            )
        if occurred_to is not None:
            statement = statement.where(AuditLogModel.occurred_at <= occurred_to)

        statement = (
            statement.order_by(AuditLogModel.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        with self._sessions() as session:
            rows = session.scalars(statement).all()
            return [
                item
                for row in rows
                if (item := self._to_schema(row)) is not None
            ]
