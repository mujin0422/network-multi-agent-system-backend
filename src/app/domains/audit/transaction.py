"""Transaction-scoped audit intent, declared by services and persisted by repositories.

The repository calls append_audit_in_session(session) before its transaction
commits. If either business data or audit insert fails, both roll back.
No ambient request body, token, credential or command data is captured.
"""

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterator

from sqlalchemy.orm import Session

from app.core.utils import generate_uuid
from app.domains.audit.models import AuditLogModel
from app.domains.audit.schemas import AuditActorType, AuditEventStatus


@dataclass(frozen=True)
class AuditIntent:
    action: str
    resource_type: str
    resource_id: str
    actor_user_id: str | None = None
    actor_display_name: str | None = None


_active_audit: ContextVar[AuditIntent | None] = ContextVar(
    "active_business_audit", default=None
)
_request_actor: ContextVar[tuple[str, str] | None] = ContextVar(
    "authenticated_audit_actor", default=None
)


def set_request_audit_actor(user_id: str, display_name: str) -> Token:
    return _request_actor.set((user_id, display_name))


def reset_request_audit_actor(token: Token) -> None:
    _request_actor.reset(token)


@contextmanager
def audit_mutation(
    action: str,
    resource_type: str,
    resource_id: str,
    *,
    actor_user_id: str | None = None,
    actor_display_name: str | None = None,
) -> Iterator[None]:
    """Service declares an action; repository persists it in its own transaction."""
    verified = _request_actor.get()
    intent = AuditIntent(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_user_id=verified[0] if verified else actor_user_id,
        actor_display_name=verified[1] if verified else actor_display_name,
    )
    token = _active_audit.set(intent)
    try:
        yield
    finally:
        _active_audit.reset(token)


def append_audit_in_session(session: Session) -> None:
    """Append audit in the SAME Session as the business mutation.

    No-op for non-audited internal writes. Database exceptions abort the
    encompassing transaction and must not be swallowed.
    """
    intent = _active_audit.get()
    if intent is None:
        return
    session.add(
        AuditLogModel(
            id=generate_uuid(),
            actor_user_id=intent.actor_user_id,
            actor_type=AuditActorType.USER if intent.actor_user_id else AuditActorType.SYSTEM,
            actor_display_name=(
                intent.actor_display_name
                or ("Authenticated user" if intent.actor_user_id else "System")
            ),
            action=intent.action,
            resource_type=intent.resource_type,
            resource_id=intent.resource_id,
            event_status=AuditEventStatus.SUCCESS,
            summary=f"{intent.action.replace('_', ' ').title()}",
            event_data={},
            occurred_at=datetime.now(UTC),
        )
    )
