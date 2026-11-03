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
from app.domains.identity.repositories import (
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserSessionRepository,
)
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
    users = UserRepository(database_url)
    roles = RoleRepository(database_url)
    permissions = RolePermissionRepository(database_url)
    sessions_repository = UserSessionRepository(database_url)
    now = datetime.now(UTC)
    roles.save_role(Role(id="role-test", name="Admin", created_at=now))
    users.save_user(
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
    return users, roles, permissions, sessions_repository, sessions


def test_user_and_role_queries_preserve_password_privacy(identity_database):
    users, roles, _, _, _ = identity_database

    assert roles.get_by_name("ADMIN").id == "role-test"
    assert len(roles.get_all()) == 1
    assert users.get_by_email("TEST@EXAMPLE.COM").password_hash == (
        "test-password-hash"
    )
    assert "password_hash" not in users.get_by_id("user-test").model_dump()
    assert "password_hash" not in users.get_all()[0].model_dump()

    user = users.get_record_by_id("user-test")
    users.save_user(user.model_copy(update={"full_name": "Updated User"}))
    users.update_login("user-test", datetime.now(UTC))
    assert users.get_by_id("user-test").full_name == "Updated User"
    assert users.get_by_id("user-test").last_login_at is not None
    role = roles.get_by_id("role-test")
    roles.save_role(role.model_copy(update={"name": "Operator"}))
    assert roles.get_by_name("operator").id == role.id


def test_role_permissions_remain_scoped_to_role(identity_database):
    _, _, permissions, _, sessions = identity_database
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

    assert permissions.get_all_permission_pairs_by_role_id("role-test") == {("Device Management", "View")}
    assert permissions.get_all_permission_pairs_by_role_id("other-role") == set()


def test_session_rotation_is_atomic_and_cannot_reuse_revoked_session(identity_database):
    _, _, _, repository, _ = identity_database
    now = datetime.now(UTC)
    original = UserSessionRecord(
        id=uuid4(),
        user_id="user-test",
        refresh_token_hash="original-hash",
        created_at=now,
        expires_at=now + timedelta(days=1),
    )
    repository.save_session(original)
    assert repository.get_by_token_hash("original-hash").id == original.id

    # Trùng hash làm INSERT thất bại; UPDATE thu hồi phiên cũ phải rollback.
    invalid = original.model_copy(update={"id": uuid4()})
    with pytest.raises(IntegrityError):
        repository.rotate_session(original.id, now, invalid)
    assert repository.get_is_active(original.id)

    replacement = original.model_copy(
        update={"id": uuid4(), "refresh_token_hash": "replacement-hash"}
    )
    assert repository.rotate_session(original.id, now, replacement)
    assert repository.get_active_by_id(original.id) is None
    assert repository.get_is_active(replacement.id)
    assert not repository.rotate_session(original.id, now, replacement)
    repository.revoke_session(replacement.id, now)
    assert not repository.get_is_active(replacement.id)
