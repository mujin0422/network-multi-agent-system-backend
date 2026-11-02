"""Facade chuyển tiếp các repository theo bảng cho Identity services."""

from datetime import datetime
from uuid import UUID

from app.domains.identity.repositories.role import RoleRepository
from app.domains.identity.repositories.role_permission import RolePermissionRepository
from app.domains.identity.repositories.user import UserRepository
from app.domains.identity.repositories.user_session import UserSessionRepository
from app.domains.identity.schemas import (
    Action,
    ManagementFunction,
    Permission,
    Role,
    RolePermission,
    User,
    UserRecord,
    UserSessionRecord,
)


class IdentityRepository:
    """Chỉ chuyển tiếp; query và transaction thuộc repository từng bảng."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo IdentityRepository cùng các phụ thuộc cần thiết."""
        self._users = UserRepository(database_url)
        self._roles = RoleRepository(database_url)
        self._role_permissions = RolePermissionRepository(database_url)
        self._user_sessions = UserSessionRepository(database_url)

    # =============================================================================
    # User — bảng users
    # =============================================================================

    def get_user_by_email(self, email: str) -> UserRecord | None:
        return self._users.get_by_email(email)

    def get_user_by_id(self, user_id: str) -> User | None:
        return self._users.get_by_id(user_id)

    def get_all_users(self) -> list[User]:
        return self._users.get_all()

    def get_user_record_by_id(self, user_id: str) -> UserRecord | None:
        return self._users.get_record_by_id(user_id)

    def save_user(self, user: UserRecord) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_user."""
        self._users.save_user(user)

    def update_login(self, user_id: str, logged_in_at: datetime) -> None:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức update_login."""
        self._users.update_login(user_id, logged_in_at)

    # =============================================================================
    # Role — bảng roles
    # =============================================================================

    def get_role_by_id(self, role_id: str) -> Role | None:
        return self._roles.get_by_id(role_id)

    def get_all_roles(self) -> list[Role]:
        return self._roles.get_all()

    def get_role_by_name(self, name: str) -> Role | None:
        return self._roles.get_by_name(name)

    def save_role(self, role: Role) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_role."""
        self._roles.save_role(role)

    # =============================================================================
    # Role Permission — tra cứu quyền được gán cho role
    # =============================================================================

    def get_all_permission_pairs_by_role_id(
        self,
        role_id: str,
    ) -> set[tuple[str, str]]:
        return self._role_permissions.get_all_permission_pairs_by_role_id(role_id)

    def get_all_actions(self) -> list[Action]:
        return self._role_permissions.get_all_actions()

    def get_all_management_functions(self) -> list[ManagementFunction]:
        return self._role_permissions.get_all_management_functions()

    def get_all_permissions(self) -> list[Permission]:
        return self._role_permissions.get_all_permissions()

    def get_all_role_permissions_by_role_id(
        self,
        role_id: str,
    ) -> list[RolePermission]:
        return self._role_permissions.get_all_by_role_id(role_id)

    def replace_role_permissions(
        self, role_id: str, permission_ids: set[str]
    ) -> list[RolePermission]:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức replace_role_permissions."""
        return self._role_permissions.replace_role_permissions(role_id, permission_ids)

    # =============================================================================
    # User Session — quản lý phiên và rotate refresh token nguyên tử
    # =============================================================================

    def save_session(self, session: UserSessionRecord) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_session."""
        self._user_sessions.save_session(session)

    def get_session_by_token_hash(self, token_hash: str) -> UserSessionRecord | None:
        return self._user_sessions.get_by_token_hash(token_hash)

    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None:
        """Kết thúc hoặc loại bỏ dữ liệu theo nghiệp vụ của phương thức revoke_session."""
        self._user_sessions.revoke_session(session_id, revoked_at)

    def get_is_session_active(self, session_id: UUID) -> bool:
        return self._user_sessions.get_is_active(session_id)

    def get_active_session_by_id(self, session_id: UUID) -> UserSessionRecord | None:
        return self._user_sessions.get_active_by_id(session_id)

    def rotate_session(
        self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord
    ) -> bool:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức rotate_session."""
        return self._user_sessions.rotate_session(session_id, revoked_at, replacement)
