"""HTTP API chỉ đọc dành cho system audit log."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.domains.audit.routers.dependencies import get_audit_log_service
from app.domains.audit.schemas import AuditEventStatus, AuditLog
from app.domains.audit.services import AuditLogService
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User


router = APIRouter()


@router.get("/", response_model=list[AuditLog], summary="Lấy danh sách audit log")
async def list_audit_logs(
    service: Annotated[AuditLogService, Depends(get_audit_log_service)],
    _: Annotated[User, Depends(require_permission("Audit Log", "View"))],
    actor_user_id: Annotated[str | None, Query(max_length=64)] = None,
    action: Annotated[str | None, Query(max_length=100)] = None,
    resource_type: Annotated[str | None, Query(max_length=100)] = None,
    event_status: AuditEventStatus | None = None,
    occurred_from: datetime | None = None,
    occurred_to: datetime | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[AuditLog]:
    """Tra cứu audit log theo actor, tài nguyên, kết quả và khoảng thời gian."""

    return service.list_logs(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        event_status=event_status,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{audit_log_id}",
    response_model=AuditLog,
    summary="Lấy chi tiết audit log",
)
async def get_audit_log(
    audit_log_id: UUID,
    service: Annotated[AuditLogService, Depends(get_audit_log_service)],
    _: Annotated[User, Depends(require_permission("Audit Log", "View"))],
) -> AuditLog:
    """Trả bản ghi audit bất biến theo UUID."""

    return service.get(audit_log_id)
