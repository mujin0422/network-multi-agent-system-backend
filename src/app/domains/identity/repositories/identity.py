"""Facade chuyển tiếp các repository theo bảng cho Identity services."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domains.identity.repositories.role import (
    RoleRepository,
    RoleRepositoryProtocol,
)
from app.domains.identity.repositories.role_permission import (
    RolePermissionRepository,
    RolePermissionRepositoryProtocol,
)
from app.domains.identity.repositories.user import (
    UserRepository,
    UserRepositoryProtocol,
)
from app.domains.identity.repositories.user_session import (
    UserSessionRepository,
    UserSessionRepositoryProtocol,
)
from app.domains.identity.schemas import Role, User, UserRecord, UserSessionRecord


class IdentityRepositoryProtocol(
    UserRepositoryProtocol,
    RoleRepositoryProtocol,
    RolePermissionRepositoryProtocol,
    UserSessionRepositoryProtocol,
    Protocol,
):
    """Contract tổng hợp giữ nguyên giao diện các service đang sử dụng."""


class IdentityRepository:
    """Chỉ chuyển tiếp; query và transaction thuộc repository từng bảng."""

    def __init__(self, database_url: str) -> None:
        self._users = UserRepository(database_url)
        self._roles = RoleRepository(database_url)
        self._role_permissions = RolePermissionRepository(database_url)
        self._user_sessions = UserSessionRepository(database_url)

    # =============================================================================
    # User — bảng users
    # =============================================================================

    def get_user_by_email(self, email: str) -> UserRecord | None:
        return self._users.get_user_by_email(email)

    def get_user(self, user_id: str) -> User | None:
        return self._users.get_user(user_id)

    def list_users(self) -> list[User]:
        return self._users.list_users()

    def get_user_with_password(self, user_id: str) -> UserRecord | None:
        return self._users.get_user_with_password(user_id)

    def save_user(self, user: UserRecord) -> None:
        self._users.save_user(user)

    def update_login(self, user_id: str, logged_in_at: datetime) -> None:
        self._users.update_login(user_id, logged_in_at)

    # =============================================================================
    # Role — bảng roles
    # =============================================================================

    def get_role(self, role_id: str) -> Role | None:
        return self._roles.get_role(role_id)

    def list_roles(self) -> list[Role]:
        return self._roles.list_roles()

    def get_role_by_name(self, name: str) -> Role | None:
        return self._roles.get_role_by_name(name)

    def save_role(self, role: Role) -> None:
        self._roles.save_role(role)

    # =============================================================================
    # Role Permission — tra cứu quyền được gán cho role
    # =============================================================================

    def get_permissions(self, role_id: str) -> set[tuple[str, str]]:
        return self._role_permissions.get_permissions(role_id)

    # =============================================================================
    # User Session — quản lý phiên và rotate refresh token nguyên tử
    # =============================================================================

    def save_session(self, session: UserSessionRecord) -> None:
        self._user_sessions.save_session(session)

    def get_session_by_hash(self, token_hash: str) -> UserSessionRecord | None:
        return self._user_sessions.get_session_by_hash(token_hash)

    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None:
        self._user_sessions.revoke_session(session_id, revoked_at)

    def is_session_active(self, session_id: UUID) -> bool:
        return self._user_sessions.is_session_active(session_id)

    def get_active_session(self, session_id: UUID) -> UserSessionRecord | None:
        return self._user_sessions.get_active_session(session_id)

    def rotate_session(
        self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord
    ) -> bool:
        return self._user_sessions.rotate_session(session_id, revoked_at, replacement)
