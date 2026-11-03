"""Services xác thực, phân quyền, quản lý user và role của Identity domain."""

from datetime import UTC, datetime
from uuid import UUID

import jwt

from app.core.config import Settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from app.core.utils import IdPrefix, generate_id, generate_uuid
from app.domains.identity.repositories import (
    RolePermissionRepository,
    RoleRepository,
    UserRepository,
    UserSessionRepository,
)
from app.domains.identity.schemas import (
    AccessTokenPayload,
    PermissionCatalog,
    Role,
    RoleCreate,
    RolePermission,
    RoleUpdate,
    TokenResponse,
    User,
    UserCreate,
    UserRecord,
    UserUpdate,
    UserStatus,
)
from app.domains.identity.utils import (
    hash_password,
    hash_refresh_token,
    issue_token_bundle,
    verify_password,
)


# =============================================================================
# Xác thực và phân quyền
# =============================================================================


class IdentityService:
    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: UserSessionRepository,
        permission_repository: RolePermissionRepository,
        settings: Settings,
    ) -> None:
        """Khởi tạo IdentityService cùng các phụ thuộc cần thiết."""
        self._users = user_repository
        self._sessions = session_repository
        self._permissions = permission_repository
        self._settings = settings

    # =============================================================================
    # Đăng nhập, làm mới và đăng xuất
    # =============================================================================

    def login(self, email: str, password: str) -> TokenResponse:
        """Xử lý xác thực theo nghiệp vụ của phương thức login."""
        user = self._users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Email hoặc mật khẩu không đúng")
        if user.user_status != UserStatus.ACTIVE:
            raise AuthenticationError("Tài khoản đã bị vô hiệu hóa")
        now = datetime.now(UTC)
        self._users.update_login(user.id, now)
        return self._new_session(user, now)

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Xoay session và phát hành cặp token mới từ refresh token hợp lệ."""

        session = self._sessions.get_by_token_hash(
            hash_refresh_token(refresh_token)
        )
        now = datetime.now(UTC)
        if not session or session.revoked_at or session.expires_at <= now:
            raise AuthenticationError("Refresh token không hợp lệ hoặc đã hết hạn")
        user = self._users.get_record_by_id(session.user_id)
        if not user or user.user_status != UserStatus.ACTIVE:
            raise AuthenticationError("Tài khoản không hoạt động")
        return self._rotate_session(user, session.id, now)

    def logout(self, session_id: UUID) -> None:
        """Kết thúc hoặc loại bỏ dữ liệu theo nghiệp vụ của phương thức logout."""
        self._sessions.revoke_session(session_id, datetime.now(UTC))

    # =============================================================================
    # Xác minh access token và kiểm tra quyền
    # =============================================================================

    def authenticate(self, token: str) -> tuple[User, UUID]:
        """Xử lý xác thực theo nghiệp vụ của phương thức authenticate."""
        try:
            data = jwt.decode(
                token,
                self._settings.auth_jwt_secret,
                algorithms=["HS256"],
                options={"require": ["sub", "sid", "iat", "exp", "jti"]},
            )
            payload = AccessTokenPayload.model_validate(data)
            session_id = UUID(payload.sid)
        except (jwt.PyJWTError, ValueError):
            raise AuthenticationError("Access token không hợp lệ hoặc đã hết hạn") from None
        # Session ID is embedded in the signed token; check the session revocation
        # state through repository method added for bearer authentication.
        session = self._sessions.get_active_by_id(session_id)
        if not session:
            raise AuthenticationError("Phiên đăng nhập đã bị thu hồi")
        user = self._users.get_by_id(payload.sub)
        if not user or user.id != session.user_id or user.user_status != UserStatus.ACTIVE:
            raise AuthenticationError("Tài khoản không hoạt động")
        return user, session_id

    def require_permission(self, user: User, function: str, action: str) -> None:
        """Kiểm tra người dùng có quyền thực hiện hành động trên chức năng."""

        if (
            function,
            action,
        ) not in self._permissions.get_all_permission_pairs_by_role_id(user.role_id):
            raise AuthorizationError("Không có quyền thực hiện thao tác này")

    # =============================================================================
    # Tạo phiên đăng nhập và phát hành token
    # =============================================================================

    def _new_session(self, user: User, now: datetime) -> TokenResponse:
        """Phát hành token và lưu session mới."""

        bundle = issue_token_bundle(user, now, generate_uuid(), self._settings)
        self._sessions.save_session(bundle.session)
        return bundle.response

    def _rotate_session(self, user: User, old_session_id: UUID, now: datetime) -> TokenResponse:
        """Phát hành token mới và xoay session theo transaction."""

        bundle = issue_token_bundle(user, now, generate_uuid(), self._settings)
        if not self._sessions.rotate_session(
            old_session_id,
            now,
            bundle.session,
        ):
            raise AuthenticationError("Refresh token đã được sử dụng")
        return bundle.response


# =============================================================================
# User
# =============================================================================


class UserService:
    """Tạo và cập nhật user, không để lộ password hash qua API."""

    def __init__(
        self,
        user_repository: UserRepository,
        role_repository: RoleRepository,
    ) -> None:
        """Khởi tạo service quản lý người dùng và role liên quan."""

        self._users = user_repository
        self._roles = role_repository

    def create_user(self, payload: UserCreate) -> User:
        """Tạo mới dữ liệu theo nghiệp vụ của phương thức create_user."""
        self._ensure_role_exists(payload.role_id)
        self._ensure_unique_email(payload.email)
        record = UserRecord(
            id=generate_id(IdPrefix.USER),
            role_id=payload.role_id,
            email=payload.email,
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            user_status=payload.user_status,
            created_at=datetime.now(UTC),
            last_updated_at=None,
            last_login_at=None,
        )
        self._users.save_user(record)
        return User.model_validate(record.model_dump())

    def list_users(self) -> list[User]:
        """Lấy danh sách user công khai, không bao gồm password hash."""

        return self._users.get_all()

    def get_user(self, user_id: str) -> User:
        """Lấy user theo ID hoặc phát sinh lỗi nếu không tồn tại."""

        user = self._users.get_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError(f"Không tìm thấy user '{user_id}'")
        return user

    def update_user(self, user_id: str, payload: UserUpdate) -> User:
        """Cập nhật thông tin, role hoặc mật khẩu của người dùng."""

        current = self._users.get_record_by_id(user_id)
        if current is None:
            raise ResourceNotFoundError(f"Không tìm thấy user '{user_id}'")

        changes = payload.model_dump(
            exclude_unset=True,
            exclude_none=True,
            exclude={"password"},
        )
        if "role_id" in changes:
            self._ensure_role_exists(changes["role_id"])
        if "email" in changes:
            self._ensure_unique_email(changes["email"], exclude_user_id=user_id)
        if payload.password is not None:
            changes["password_hash"] = hash_password(payload.password)
        changes["last_updated_at"] = datetime.now(UTC)

        updated = current.model_copy(update=changes)
        self._users.save_user(updated)
        return User.model_validate(updated.model_dump())

    def _ensure_role_exists(self, role_id: str) -> None:
        """Bảo đảm role được gán cho người dùng tồn tại."""

        if self._roles.get_by_id(role_id) is None:
            raise ResourceNotFoundError(f"Không tìm thấy role '{role_id}'")

    def _ensure_unique_email(
        self,
        email: str,
        exclude_user_id: str | None = None,
    ) -> None:
        """Kiểm tra điều kiện nghiệp vụ trong phương thức _ensure_unique_email."""
        existing = self._users.get_by_email(email)
        if existing is not None and existing.id != exclude_user_id:
            raise ResourceConflictError(f"Email '{email}' đã được sử dụng")


# =============================================================================
# Role
# =============================================================================


class RoleService:
    """Tạo và cập nhật role cùng thông tin audit."""

    def __init__(self, role_repository: RoleRepository) -> None:
        """Khởi tạo service quản lý role."""

        self._roles = role_repository

    def create_role(self, payload: RoleCreate, actor_id: str) -> Role:
        """Tạo mới dữ liệu theo nghiệp vụ của phương thức create_role."""
        self._ensure_unique_name(payload.name)
        now = datetime.now(UTC)
        role = Role(
            id=generate_id(IdPrefix.ROLE),
            **payload.model_dump(),
            created_by=actor_id,
            last_updated_by=actor_id,
            created_at=now,
            last_updated_at=now,
        )
        self._roles.save_role(role)
        return role

    def list_roles(self) -> list[Role]:
        """Lấy danh sách role hiện có."""

        return self._roles.get_all()

    def get_role(self, role_id: str) -> Role:
        """Lấy role theo ID hoặc phát sinh lỗi nếu không tồn tại."""

        role = self._roles.get_by_id(role_id)
        if role is None:
            raise ResourceNotFoundError(f"Không tìm thấy role '{role_id}'")
        return role

    def update_role(
        self,
        role_id: str,
        payload: RoleUpdate,
        actor_id: str,
    ) -> Role:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức update_role."""
        current = self.get_role(role_id)

        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if "name" in changes:
            self._ensure_unique_name(changes["name"], exclude_role_id=role_id)
        if "description" in payload.model_fields_set:
            changes["description"] = payload.description
        changes.update(
            last_updated_by=actor_id,
            last_updated_at=datetime.now(UTC),
        )
        updated = current.model_copy(update=changes)
        self._roles.save_role(updated)
        return updated

    def _ensure_unique_name(
        self,
        name: str,
        exclude_role_id: str | None = None,
    ) -> None:
        """Khởi tạo service quản lý ma trận phân quyền."""

        """Kiểm tra điều kiện nghiệp vụ trong phương thức _ensure_unique_name."""
        existing = self._roles.get_by_name(name)
        if existing is not None and existing.id != exclude_role_id:
            raise ResourceConflictError(f"Tên role '{name}' đã được sử dụng")


class AccessControlService:
    """Đọc catalog và thay thế ma trận quyền của từng role."""

    def __init__(
        self,
        role_repository: RoleRepository,
        permission_repository: RolePermissionRepository,
    ) -> None:
        """Khởi tạo service quản lý catalog và quyền theo role."""

        self._roles = role_repository
        self._permissions = permission_repository

    def get_catalog(self) -> PermissionCatalog:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_catalog."""
        return PermissionCatalog(
            functions=self._permissions.get_all_management_functions(),
            actions=self._permissions.get_all_actions(),
            permissions=self._permissions.get_all_permissions(),
        )

    def list_role_permissions(self, role_id: str) -> list[RolePermission]:
        """Truy vấn danh sách dữ liệu theo phạm vi của phương thức list_role_permissions."""
        self._require_role(role_id, require_mutable=False)
        return self._permissions.get_all_by_role_id(role_id)

    def replace_role_permissions(
        self, role_id: str, permission_ids: list[str]
    ) -> list[RolePermission]:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức replace_role_permissions."""
        self._require_role(role_id, require_mutable=True)
        requested = set(permission_ids)
        valid = {item.id for item in self._permissions.get_all_permissions()}
        unknown = sorted(requested - valid)
        if unknown:
            raise ResourceNotFoundError(
                f"Không tìm thấy permission: {', '.join(unknown)}"
            )
        return self._permissions.replace_role_permissions(role_id, requested)

    def _require_role(self, role_id: str, *, require_mutable: bool) -> Role:
        """Lấy role và kiểm tra role có được phép chỉnh sửa hay không."""

        role = self._roles.get_by_id(role_id)
        if role is None:
            raise ResourceNotFoundError(f"Không tìm thấy role '{role_id}'")
        if require_mutable and role.name.casefold() == "super admin":
            raise ResourceConflictError("Không thể sửa quyền của Super Admin")
        return role
