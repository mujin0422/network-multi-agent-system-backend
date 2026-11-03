"""Use cases ghi nhận và tra cứu system audit log."""

from datetime import UTC, datetime
from uuid import UUID

from app.core.exceptions import ResourceNotFoundError
from app.core.utils import generate_uuid
from app.domains.audit.repositories import AuditLogRepository
from app.domains.audit.schemas import AuditEventStatus, AuditLog, AuditLogCreate


class AuditLogService:
    """Cung cấp thao tác append nội bộ và truy vấn audit log chỉ đọc."""

    def __init__(self, repository: AuditLogRepository) -> None:
        """Khởi tạo service cùng repository audit log."""

        self._repository = repository

    def record(self, payload: AuditLogCreate) -> AuditLog:
        """Tạo audit log mới với UUID và thời điểm do Backend kiểm soát."""

        audit_log = AuditLog(
            id=generate_uuid(),
            occurred_at=datetime.now(UTC),
            **payload.model_dump(),
        )
        self._repository.save(audit_log)
        return audit_log

    def get(self, audit_log_id: UUID) -> AuditLog:
        """Trả audit log theo ID hoặc phát sinh lỗi 404 ở HTTP layer."""

        audit_log = self._repository.get_by_id(audit_log_id)
        if audit_log is None:
            raise ResourceNotFoundError(f"Không tìm thấy audit log '{audit_log_id}'")
        return audit_log

    def list_logs(
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
        """Ủy quyền truy vấn có phân trang và bộ lọc cho repository."""

        return self._repository.get_all(
            actor_user_id=actor_user_id,
            action=action.upper() if action is not None else None,
            resource_type=(
                resource_type.upper() if resource_type is not None else None
            ),
            event_status=event_status,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            offset=offset,
            limit=limit,
        )
