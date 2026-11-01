"""Kiểm thử repository, service và quy tắc bảo mật của System Audit domain."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.core.database import Base, create_session_factory
from app.core.exceptions import ResourceNotFoundError
from app.domains.audit.models import AuditLogModel
from app.domains.audit.repositories import AuditLogRepository
from app.domains.audit.schemas import (
    AuditActorType,
    AuditEventStatus,
    AuditLogCreate,
)
from app.domains.audit.services import AuditLogService
from app.domains.identity.models import UserModel  # noqa: F401 - resolve audit FK


@pytest.fixture
def audit_service(tmp_path) -> AuditLogService:
    database_url = f"sqlite:///{tmp_path / 'audit.db'}"
    sessions = create_session_factory(database_url)
    Base.metadata.create_all(
        sessions.kw["bind"],
        tables=[AuditLogModel.__table__],
    )
    return AuditLogService(AuditLogRepository(database_url))


def test_record_and_filter_audit_logs(audit_service: AuditLogService) -> None:
    first = audit_service.record(
        AuditLogCreate(
            actor_type=AuditActorType.SYSTEM,
            actor_display_name="Identity Service",
            action="session_rotated",
            resource_type="user_session",
            resource_id="session-1",
            event_status=AuditEventStatus.SUCCESS,
            event_data={"reason": "refresh"},
        )
    )
    second = audit_service.record(
        AuditLogCreate(
            actor_type=AuditActorType.AGENT,
            actor_display_name="Network Agent",
            action="command_rejected",
            resource_type="device",
            resource_id="devc-1",
            event_status=AuditEventStatus.DENIED,
        )
    )

    assert audit_service.get(first.id).action == "SESSION_ROTATED"
    assert [item.id for item in audit_service.list_logs(resource_type="device")] == [
        second.id
    ]
    assert [
        item.id
        for item in audit_service.list_logs(event_status=AuditEventStatus.SUCCESS)
    ] == [first.id]
    assert len(
        audit_service.list_logs(
            occurred_from=datetime.now(UTC) - timedelta(minutes=1),
            limit=1,
        )
    ) == 1


def test_audit_log_rejects_missing_user_and_sensitive_metadata() -> None:
    with pytest.raises(ValidationError):
        AuditLogCreate(
            actor_type=AuditActorType.USER,
            action="USER_UPDATED",
            resource_type="USER",
            event_status=AuditEventStatus.SUCCESS,
        )

    with pytest.raises(ValidationError):
        AuditLogCreate(
            actor_type=AuditActorType.SYSTEM,
            action="LOGIN_FAILED",
            resource_type="USER_SESSION",
            event_status=AuditEventStatus.FAILED,
            event_data={"request": {"password": "must-not-be-stored"}},
        )


def test_get_unknown_audit_log_raises_not_found(
    audit_service: AuditLogService,
) -> None:
    from uuid import uuid4

    with pytest.raises(ResourceNotFoundError):
        audit_service.get(uuid4())
