"""Unit tests for IdentityService authentication and RBAC behavior."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.domains.identity.schemas import User, UserRecord, UserStatus
from app.domains.identity.services import IdentityService


class MemoryIdentityRepository:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.user = UserRecord(
            id="user-test", role_id="role-test", email="test@example.com",
            password_hash=IdentityService.hash_password("correct-password"),
            full_name="Test User", user_status=UserStatus.ACTIVE,
            created_at=now,
        )
        self.sessions = {}
        self.permissions = {("Device Management", "View")}

    def get_user_by_email(self, email):
        return self.user if email == self.user.email else None

    def get_user(self, user_id):
        return User.model_validate(self.user.model_dump()) if user_id == self.user.id else None

    def get_user_with_password(self, user_id):
        return self.user if user_id == self.user.id else None

    def get_role(self, role_id):
        return None

    def get_permissions(self, role_id):
        return set(self.permissions)

    def save_session(self, session):
        self.sessions[session.id] = session

    def get_session_by_hash(self, token_hash):
        return next((s for s in self.sessions.values() if s.refresh_token_hash == token_hash), None)

    def revoke_session(self, session_id, revoked_at):
        old = self.sessions[session_id]
        self.sessions[session_id] = old.model_copy(update={"revoked_at": revoked_at})

    def is_session_active(self, session_id):
        s = self.sessions.get(session_id)
        return bool(s and not s.revoked_at and s.expires_at > datetime.now(UTC))

    def get_active_session(self, session_id):
        return self.sessions.get(session_id) if self.is_session_active(session_id) else None

    def rotate_session(self, session_id, revoked_at, replacement):
        if not self.is_session_active(session_id):
            return False
        self.revoke_session(session_id, revoked_at)
        self.save_session(replacement)
        return True

    def update_login(self, user_id, logged_in_at):
        self.user = self.user.model_copy(update={"last_login_at": logged_in_at})


@pytest.fixture
def identity():
    repo = MemoryIdentityRepository()
    settings = Settings(auth_jwt_secret="unit-test-secret", auth_access_token_minutes=15)
    return IdentityService(repo, settings), repo


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


def test_permission_is_loaded_from_role_permissions(identity):
    service, repo = identity
    user = User.model_validate(repo.user.model_dump())
    service.require_permission(user, "Device Management", "View")
    with pytest.raises(AuthorizationError):
        service.require_permission(user, "Device Management", "Delete")
