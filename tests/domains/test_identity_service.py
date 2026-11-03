"""Unit tests for IdentityService authentication and RBAC behavior."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.domains.identity.schemas import (
    Action,
    ManagementFunction,
    Permission,
    Role,
    RolePermission,
    User,
    UserCreate,
    UserRecord,
    UserStatus,
)
from app.domains.identity.services import AccessControlService, IdentityService
from app.domains.identity.utils import hash_password


class MemoryIdentityStore:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.user = UserRecord(
            id="user-test", role_id="role-test", email="test@example.com",
            password_hash=hash_password("correct-password"),
            full_name="Test User", user_status=UserStatus.ACTIVE,
            created_at=now,
        )
        self.sessions = {}
        self.permissions = {("Device Management", "View")}

    def get_by_email(self, email):
        return self.user if email == self.user.email else None

    def get_by_id(self, user_id):
        return User.model_validate(self.user.model_dump()) if user_id == self.user.id else None

    def get_record_by_id(self, user_id):
        return self.user if user_id == self.user.id else None

    def get_role_by_id(self, role_id):
        return None

    def get_all_permission_pairs_by_role_id(self, role_id):
        return set(self.permissions)

    def save_session(self, session):
        self.sessions[session.id] = session

    def get_by_token_hash(self, token_hash):
        return next((s for s in self.sessions.values() if s.refresh_token_hash == token_hash), None)

    def revoke_session(self, session_id, revoked_at):
        old = self.sessions[session_id]
        self.sessions[session_id] = old.model_copy(update={"revoked_at": revoked_at})

    def get_is_session_active(self, session_id):
        s = self.sessions.get(session_id)
        return bool(s and not s.revoked_at and s.expires_at > datetime.now(UTC))

    def get_active_by_id(self, session_id):
        return self.sessions.get(session_id) if self.get_is_session_active(session_id) else None

    def rotate_session(self, session_id, revoked_at, replacement):
        if not self.get_is_session_active(session_id):
            return False
        self.revoke_session(session_id, revoked_at)
        self.save_session(replacement)
        return True

    def update_login(self, user_id, logged_in_at):
        self.user = self.user.model_copy(update={"last_login_at": logged_in_at})


@pytest.fixture
def identity():
    repo = MemoryIdentityStore()
    settings = Settings(auth_jwt_secret="unit-test-secret", auth_access_token_minutes=15)
    return IdentityService(repo, repo, repo, settings), repo


def test_login_authenticate_refresh_and_logout(identity):
    service, repo = identity
    tokens = service.login("test@example.com", "correct-password")
    user, _ = service.authenticate(tokens.access_token)
    assert user.id == "user-test"

    rotated = service.refresh(tokens.refresh_token)
    with pytest.raises(AuthenticationError):
        service.refresh(tokens.refresh_token)
    with pytest.raises(AuthenticationError):
        service.authenticate(tokens.access_token)
    _, rotated_session_id = service.authenticate(rotated.access_token)
    service.logout(rotated_session_id)
    with pytest.raises(AuthenticationError):
        service.authenticate(rotated.access_token)
    assert len(repo.sessions) == 2


def test_login_rejects_bad_password_and_disabled_user(identity):
    service, repo = identity
    with pytest.raises(AuthenticationError):
        service.login("test@example.com", "wrong-password")
    repo.user = repo.user.model_copy(update={"user_status": UserStatus.DISABLED})
    with pytest.raises(AuthenticationError):
        service.login("test@example.com", "correct-password")


def test_authenticate_rejects_forged_and_expired_access_tokens(identity):
    service, repo = identity
    tokens = service.login("test@example.com", "correct-password")

    forged = jwt.encode(
        jwt.decode(tokens.access_token, options={"verify_signature": False}),
        "different-secret",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        service.authenticate(forged)

    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": "user-test",
            "sid": str(next(iter(repo.sessions))),
            "iat": now - timedelta(minutes=2),
            "exp": now - timedelta(minutes=1),
            "jti": "expired-token",
        },
        "unit-test-secret",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        service.authenticate(expired)


def test_user_password_rejects_values_longer_than_bcrypt_limit():
    with pytest.raises(ValidationError):
        UserCreate(
            role_id="role-test",
            email="test@example.com",
            password="á" * 37,
            full_name="Test User",
        )


def test_production_rejects_default_or_short_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(app_env="production", auth_jwt_secret="short-secret")

    settings = Settings(app_env="production", auth_jwt_secret="x" * 32)
    assert settings.auth_jwt_secret == "x" * 32


def test_permission_is_loaded_from_role_permissions(identity):
    service, repo = identity
    user = User.model_validate(repo.user.model_dump())
    service.require_permission(user, "Device Management", "View")
    with pytest.raises(AuthorizationError):
        service.require_permission(user, "Device Management", "Delete")


class MemoryAccessControlRepository:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.roles = {
            "role-admin": Role(id="role-admin", name="Super Admin", created_at=now),
            "role-operator": Role(id="role-operator", name="Operator", created_at=now),
        }
        self.role_permissions = {
            "role-operator": [
                RolePermission(role_id="role-operator", permission_id="perm-view")
            ]
        }

    def get_by_id(self, role_id):
        return self.roles.get(role_id)

    def get_all_actions(self):
        return [Action(id="act-view", name="View")]

    def get_all_management_functions(self):
        return [ManagementFunction(id="func-device", name="Device Management")]

    def get_all_permissions(self):
        return [Permission(id="perm-view", function_id="func-device", action_id="act-view")]

    def get_all_by_role_id(self, role_id):
        return self.role_permissions.get(role_id, [])

    def replace_role_permissions(self, role_id, permission_ids):
        rows = [RolePermission(role_id=role_id, permission_id=item) for item in sorted(permission_ids)]
        self.role_permissions[role_id] = rows
        return rows


def test_access_control_catalog_and_role_permission_replacement() -> None:
    repository = MemoryAccessControlRepository()
    service = AccessControlService(repository, repository)

    catalog = service.get_catalog()
    rows = service.replace_role_permissions("role-operator", [])

    assert [item.name for item in catalog.functions] == ["Device Management"]
    assert rows == []


def test_access_control_rejects_unknown_permission_and_super_admin_changes() -> None:
    repository = MemoryAccessControlRepository()
    service = AccessControlService(repository, repository)

    with pytest.raises(ResourceNotFoundError):
        service.replace_role_permissions("role-operator", ["perm-unknown"])
    with pytest.raises(ResourceConflictError):
        service.replace_role_permissions("role-admin", ["perm-view"])
