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


def test_service_owned_uow_commits_business_and_audit_together(tmp_path):
    """Explicit UoW: both records commit, and a raised error rolls back both."""
    from app.core.database import DatabaseUnitOfWork
    from app.domains.audit.transaction import record_audit_in_session

    database_url = f"sqlite:///{tmp_path / 'service-uow.db'}"
    sessions = create_session_factory(database_url)
    Base.metadata.create_all(
        sessions.kw["bind"],
        tables=[RoleModel.__table__, AuditLogModel.__table__],
    )
    uow = DatabaseUnitOfWork.from_url(database_url)
    record = Role(
        id="role-uow-test",
        name="Before",
        created_at=datetime.now(UTC),
    )

    with uow.begin() as session:
        RoleRepository.save_role_in_session(session, record)
        record_audit_in_session(
            session, action="ROLE_CREATE", resource_type="ROLE",
            resource_id=record.id,
        )

    with sessions() as session:
        assert session.get(RoleModel, record.id).name == "Before"
        assert session.scalar(
            select(func.count()).select_from(AuditLogModel)
        ) == 1

    with pytest.raises(RuntimeError, match="forced rollback"):
        with uow.begin() as session:
            RoleRepository.save_role_in_session(
                session, record.model_copy(
                    update={"name": "SHOULD NOT BE SAVED"}
                )
            )
            record_audit_in_session(
                session, action="ROLE_UPDATE", resource_type="ROLE",
                resource_id=record.id,
            )
            raise RuntimeError("forced rollback")

    with sessions() as session:
        assert session.get(RoleModel, record.id).name == "Before"
        assert session.scalar(
            select(func.count()).select_from(AuditLogModel)
        ) == 1


def test_service_owned_uow_rolls_back_business_when_audit_insert_fails(
    tmp_path, monkeypatch
):
    """A failed audit insert must not leave a successfully updated role."""
    from app.core.database import DatabaseUnitOfWork
    from app.domains.audit.transaction import record_audit_in_session

    database_url = f"sqlite:///{tmp_path / 'failing-uow.db'}"
    sessions = create_session_factory(database_url)
    Base.metadata.create_all(
        sessions.kw["bind"],
        tables=[RoleModel.__table__, AuditLogModel.__table__],
    )
    uow = DatabaseUnitOfWork.from_url(database_url)
    record = Role(id="role-fail", name="Before", created_at=datetime.now(UTC))
    with uow.begin() as session:
        RoleRepository.save_role_in_session(session, record)
        record_audit_in_session(
            session, action="ROLE_CREATE", resource_type="ROLE",
            resource_id=record.id,
        )
    with sessions() as session:
        initial_audit_id = session.scalar(select(AuditLogModel.id))

    monkeypatch.setattr(
        "app.domains.audit.services.audit_log.generate_uuid",
        lambda: initial_audit_id,
    )
    with pytest.raises(IntegrityError):
        with uow.begin() as session:
            RoleRepository.save_role_in_session(
                session, record.model_copy(update={"name": "MUST ROLLBACK"})
            )
            record_audit_in_session(
                session, action="ROLE_UPDATE", resource_type="ROLE",
                resource_id=record.id,
            )

    with sessions() as session:
        assert session.get(RoleModel, record.id).name == "Before"
        assert session.scalar(
            select(func.count()).select_from(AuditLogModel)
        ) == 1


def test_actual_role_service_uses_one_uow_and_records_authenticated_actor(tmp_path):
    """Dependency-injected UoW is used by the real RoleService, not only helpers."""
    from app.core.database import DatabaseUnitOfWork
    from app.domains.audit.transaction import (
        reset_request_audit_actor,
        set_request_audit_actor,
    )
    from app.domains.identity.repositories import IdentityRepository
    from app.domains.identity.schemas import RoleCreate
    from app.domains.identity.services import RoleService
    from app.domains.identity.schemas import UserStatus

    database_url = f"sqlite:///{tmp_path / 'role-service-uow.db'}"
    sessions = create_session_factory(database_url)
    Base.metadata.create_all(
        sessions.kw["bind"],
        tables=[
            RoleModel.__table__,
            UserModel.__table__,
            AuditLogModel.__table__,
        ],
    )
    with sessions.begin() as session:
        session.add(
            RoleModel(
                id="role-admin", name="Super Admin",
                created_at=datetime.now(UTC),
            )
        )
        session.add(
            UserModel(
                id="user-admin", role_id="role-admin",
                email="admin@example.test", password_hash="not-a-real-password",
                full_name="Admin", user_status=UserStatus.ACTIVE,
                created_at=datetime.now(UTC),
            )
        )

    service = RoleService(
        IdentityRepository(database_url),
        uow=DatabaseUnitOfWork.from_url(database_url),
    )
    token = set_request_audit_actor("user-admin", "Admin")
    try:
        result = service.create_role(
            RoleCreate(name="Operator"), actor_id="user-admin"
        )
    finally:
        reset_request_audit_actor(token)

    with sessions() as session:
        assert session.get(RoleModel, result.id).name == "Operator"
        event = session.scalar(
            select(AuditLogModel).where(AuditLogModel.action == "ROLE_CREATE")
        )
        assert event is not None
        assert event.actor_user_id == "user-admin"
        assert event.resource_id == result.id
