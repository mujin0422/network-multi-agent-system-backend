"""Kiểm thử repository đã tách với database SQLite tạm, không cần PostgreSQL."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import Base, create_session_factory
from app.domains.identity.models import (
    ActionModel,
    ManagementFunctionModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserModel,
    UserSessionModel,
)
from app.domains.identity.repositories import IdentityRepository
from app.domains.identity.schemas import Role, UserRecord, UserSessionRecord, UserStatus


@pytest.fixture
def identity_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'identity.db'}"
    sessions = create_session_factory(database_url)
    tables = [
        RoleModel.__table__,
        UserModel.__table__,
        ManagementFunctionModel.__table__,
        ActionModel.__table__,
        PermissionModel.__table__,
        RolePermissionModel.__table__,
        UserSessionModel.__table__,
    ]
    Base.metadata.create_all(sessions.kw["bind"], tables=tables)
    repository = IdentityRepository(database_url)
    now = datetime.now(UTC)
    repository.save_role(Role(id="role-test", name="Admin", created_at=now))
    repository.save_user(
        UserRecord(
            id="user-test",
            role_id="role-test",
            email="test@example.com",
            password_hash="test-password-hash",
            full_name="Test User",
            user_status=UserStatus.ACTIVE,
            created_at=now,
        )
    )
    return repository, sessions


def test_user_and_role_queries_preserve_password_privacy(identity_database):
    repository, _ = identity_database

    assert repository.get_role_by_name("ADMIN").id == "role-test"
    assert len(repository.list_roles()) == 1
    assert repository.get_user_by_email("TEST@EXAMPLE.COM").password_hash == (
        "test-password-hash"
    )
    assert "password_hash" not in repository.get_user("user-test").model_dump()
    assert "password_hash" not in repository.list_users()[0].model_dump()

    user = repository.get_user_with_password("user-test")
    repository.save_user(user.model_copy(update={"full_name": "Updated User"}))
    repository.update_login("user-test", datetime.now(UTC))
    assert repository.get_user("user-test").full_name == "Updated User"
    assert repository.get_user("user-test").last_login_at is not None
    role = repository.get_role("role-test")
    repository.save_role(role.model_copy(update={"name": "Operator"}))
    assert repository.get_role_by_name("operator").id == role.id


def test_role_permissions_remain_scoped_to_role(identity_database):
    repository, sessions = identity_database
    with sessions.begin() as session:
        session.add(ManagementFunctionModel(id="func-test", name="Device Management"))
        session.add(ActionModel(id="act-test", name="View"))
        session.flush()
        session.add(
            PermissionModel(
                id="perm-test", function_id="func-test", action_id="act-test"
            )
        )
        session.flush()
        session.add(RolePermissionModel(role_id="role-test", permission_id="perm-test"))

    assert repository.get_permissions("role-test") == {("Device Management", "View")}
    assert repository.get_permissions("other-role") == set()


def test_session_rotation_is_atomic_and_cannot_reuse_revoked_session(identity_database):
    repository, _ = identity_database
    now = datetime.now(UTC)
    original = UserSessionRecord(
        id=uuid4(),
        user_id="user-test",
        refresh_token_hash="original-hash",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    repository.save_session(original)
    assert repository.get_session_by_hash("original-hash").id == original.id

    # Trùng hash làm INSERT thất bại; UPDATE thu hồi phiên cũ phải rollback.
    invalid = original.model_copy(update={"id": uuid4()})
    with pytest.raises(IntegrityError):
        repository.rotate_session(original.id, now, invalid)
    assert repository.is_session_active(original.id)

    replacement = original.model_copy(
        update={"id": uuid4(), "refresh_token_hash": "replacement-hash"}
    )
    assert repository.rotate_session(original.id, now, replacement)
    assert repository.get_active_session(original.id) is None
    assert repository.is_session_active(replacement.id)
    assert not repository.rotate_session(original.id, now, replacement)
    repository.revoke_session(replacement.id, now)
    assert not repository.is_session_active(replacement.id)
