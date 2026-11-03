"""Business writes and their system audit must share one SQLAlchemy commit."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.database import Base, create_session_factory
from app.domains.audit.models import AuditLogModel
from app.domains.audit.transaction import audit_mutation
from app.domains.identity.models import UserModel  # noqa: F401; resolves audit/user FKs
from app.domains.identity.models import RoleModel
from app.domains.identity.repositories.role import RoleRepository
from app.domains.identity.schemas import Role


def test_role_mutation_and_audit_commit_or_rollback_together(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'atomic-audit.db'}"
    sessions = create_session_factory(database_url)
    Base.metadata.create_all(
        sessions.kw["bind"],
        tables=[RoleModel.__table__, AuditLogModel.__table__],
    )
    repository = RoleRepository(database_url)
    record = Role(
        id="role-audit-test",
        name="Network Operator",
        created_at=datetime.now(UTC),
    )

    with audit_mutation("ROLE_CREATE", "ROLE", record.id):
        repository.save_role(record)

    with sessions() as session:
        audit = session.scalar(select(AuditLogModel))
        assert audit is not None
        assert audit.action == "ROLE_CREATE"
        assert audit.resource_id == record.id
        assert session.get(RoleModel, record.id).name == "Network Operator"

    # The audit INSERT now collides with a previous UUID. The business UPDATE
    # must not survive a failed audit flush/commit.
    monkeypatch.setattr(
        "app.domains.audit.services.audit_log.generate_uuid",
        lambda: audit.id,
    )
    with pytest.raises(IntegrityError):
        with audit_mutation("ROLE_UPDATE", "ROLE", record.id):
            repository.save_role(
                record.model_copy(update={
                    "name": "MUST ROLLBACK",
                    "last_updated_at": datetime.now(UTC),
                })
            )

    with sessions() as session:
        assert session.get(RoleModel, record.id).name == "Network Operator"
        assert session.scalar(
            select(func.count()).select_from(AuditLogModel)
        ) == 1


def test_nested_audit_intent_restores_previous_context():
    from app.domains.audit.transaction import _active_audit

    with audit_mutation("ROLE_CREATE", "ROLE", "role-1"):
        assert _active_audit.get().resource_id == "role-1"
        with audit_mutation("ROLE_UPDATE", "ROLE", "role-2"):
            assert _active_audit.get().resource_id == "role-2"
        assert _active_audit.get().resource_id == "role-1"
    assert _active_audit.get() is None
