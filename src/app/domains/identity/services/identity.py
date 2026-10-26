"""Services xác thực, phân quyền, quản lý user và role của Identity domain."""

import secrets
from datetime import UTC, datetime, timedelta
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
from app.domains.identity.repositories import IdentityRepositoryProtocol
from app.domains.identity.schemas import (
    AccessTokenPayload,
    Role,
    RoleCreate,
    RoleUpdate,
    TokenResponse,
    User,
    UserCreate,
    UserRecord,
    UserUpdate,
    UserSessionRecord,
    UserStatus,
)
from app.domains.identity.utils import (
    hash_password,
    hash_refresh_token,
    verify_password,
)


# =============================================================================
# Xác thực và phân quyền
# =============================================================================


class IdentityService:
    def __init__(
        self,
        repository: IdentityRepositoryProtocol,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._settings = settings

    # =============================================================================
    # Đăng nhập, làm mới và đăng xuất
    # =============================================================================

    def login(self, email: str, password: str) -> TokenResponse:
        user = self._repository.get_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Email hoặc mật khẩu không đúng")
        if user.user_status != UserStatus.ACTIVE:
            raise AuthenticationError("Tài khoản đã bị vô hiệu hóa")
        now = datetime.now(UTC)
        self._repository.update_login(user.id, now)
        return self._new_session(user, now)

    def refresh(self, refresh_token: str) -> TokenResponse:
        session = self._repository.get_session_by_hash(hash_refresh_token(refresh_token))
        now = datetime.now(UTC)
        if not session or session.revoked_at or session.expires_at <= now:
            raise AuthenticationError("Refresh token không hợp lệ hoặc đã hết hạn")
        user = self._repository.get_user_with_password(session.user_id)
        if not user or user.user_status != UserStatus.ACTIVE:
            raise AuthenticationError("Tài khoản không hoạt động")
        return self._rotate_session(user, session.id, now)

    def logout(self, session_id: UUID) -> None:
        self._repository.revoke_session(session_id, datetime.now(UTC))

    # =============================================================================
    # Xác minh access token và kiểm tra quyền
    # =============================================================================

    def authenticate(self, token: str) -> tuple[User, UUID]:
        try:
            data = jwt.decode(token, self._settings.auth_jwt_secret, algorithms=["HS256"])
            payload = AccessTokenPayload.model_validate(data)
            session_id = UUID(payload.sid)
        except (jwt.PyJWTError, ValueError):
            raise AuthenticationError("Access token không hợp lệ hoặc đã hết hạn") from None
        # Session ID is embedded in the signed token; check the session revocation
        # state through repository method added for bearer authentication.
        session = self._repository.get_active_session(session_id)
        if not session:
            raise AuthenticationError("Phiên đăng nhập đã bị thu hồi")
        user = self._repository.get_user(payload.sub)
        if not user or user.id != session.user_id or user.user_status != UserStatus.ACTIVE:
            raise AuthenticationError("Tài khoản không hoạt động")
        return user, session_id

    def require_permission(self, user: User, function: str, action: str) -> None:
        if (function, action) not in self._repository.get_permissions(user.role_id):
            raise AuthorizationError("Không có quyền thực hiện thao tác này")

    # =============================================================================
    # Tạo phiên đăng nhập và phát hành token
    # =============================================================================

    def _new_session(self, user: User, now: datetime) -> TokenResponse:
        return self._issue_tokens(user, now, generate_uuid(), save_session=True)

    def _rotate_session(self, user: User, old_session_id: UUID, now: datetime) -> TokenResponse:
        response = self._issue_tokens(user, now, generate_uuid(), save_session=False)
        new_session = self._session_record(user.id, response.refresh_token, response.access_token, now)
        if not self._repository.rotate_session(old_session_id, now, new_session):
            raise AuthenticationError("Refresh token đã được sử dụng")
        return response

    def _session_record(self, user_id: str, refresh: str, access: str, now: datetime) -> UserSessionRecord:
        claims = jwt.decode(access, self._settings.auth_jwt_secret, algorithms=["HS256"])
        return UserSessionRecord(
            id=UUID(claims["sid"]),
            user_id=user_id,
            refresh_token_hash=hash_refresh_token(refresh),
            expires_at=now + timedelta(days=self._settings.auth_refresh_token_days),
            created_at=now,
        )

    def _issue_tokens(self, user: User, now: datetime, session_id: UUID, *, save_session: bool) -> TokenResponse:
        raw_refresh = secrets.token_urlsafe(48)
        expires = now + timedelta(days=self._settings.auth_refresh_token_days)
        session = UserSessionRecord(
            id=session_id,
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(raw_refresh),
            expires_at=expires,
            created_at=now,
        )
        if save_session:
            self._repository.save_session(session)
        access_expires = now + timedelta(minutes=self._settings.auth_access_token_minutes)
        access = jwt.encode(
            {"sub": user.id, "sid": str(session_id), "iat": now, "exp": access_expires, "jti": secrets.token_urlsafe(12)},
            self._settings.auth_jwt_secret,
            algorithm="HS256",
        )
        return TokenResponse(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=self._settings.auth_access_token_minutes * 60,
            user=User.model_validate(user.model_dump()),
        )


# =============================================================================
# User
# =============================================================================


class UserService:
    """Tạo và cập nhật user, không để lộ password hash qua API."""

    def __init__(self, repository: IdentityRepositoryProtocol) -> None:
        self._repository = repository

    def create_user(self, payload: UserCreate) -> User:
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
        self._repository.save_user(record)
        return User.model_validate(record.model_dump())

    def list_users(self) -> list[User]:
        """Lấy danh sách user công khai, không bao gồm password hash."""

        return self._repository.list_users()

    def get_user(self, user_id: str) -> User:
        """Lấy user theo ID hoặc phát sinh lỗi nếu không tồn tại."""

        user = self._repository.get_user(user_id)
        if user is None:
            raise ResourceNotFoundError(f"Không tìm thấy user '{user_id}'")
        return user

    def update_user(self, user_id: str, payload: UserUpdate) -> User:
        current = self._repository.get_user_with_password(user_id)
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
        self._repository.save_user(updated)
        return User.model_validate(updated.model_dump())

    def _ensure_role_exists(self, role_id: str) -> None:
        if self._repository.get_role(role_id) is None:
            raise ResourceNotFoundError(f"Không tìm thấy role '{role_id}'")

    def _ensure_unique_email(
        self,
        email: str,
        exclude_user_id: str | None = None,
    ) -> None:
        existing = self._repository.get_user_by_email(email)
        if existing is not None and existing.id != exclude_user_id:
            raise ResourceConflictError(f"Email '{email}' đã được sử dụng")


# =============================================================================
# Role
# =============================================================================


class RoleService:
    """Tạo và cập nhật role cùng thông tin audit."""

    def __init__(self, repository: IdentityRepositoryProtocol) -> None:
        self._repository = repository

    def create_role(self, payload: RoleCreate, actor_id: str) -> Role:
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
        self._repository.save_role(role)
        return role

    def list_roles(self) -> list[Role]:
        """Lấy danh sách role hiện có."""

        return self._repository.list_roles()

    def get_role(self, role_id: str) -> Role:
        """Lấy role theo ID hoặc phát sinh lỗi nếu không tồn tại."""

        role = self._repository.get_role(role_id)
        if role is None:
            raise ResourceNotFoundError(f"Không tìm thấy role '{role_id}'")
        return role

    def update_role(
        self,
        role_id: str,
        payload: RoleUpdate,
        actor_id: str,
    ) -> Role:
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
        self._repository.save_role(updated)
        return updated

    def _ensure_unique_name(
        self,
        name: str,
        exclude_role_id: str | None = None,
    ) -> None:
        existing = self._repository.get_role_by_name(name)
        if existing is not None and existing.id != exclude_role_id:
            raise ResourceConflictError(f"Tên role '{name}' đã được sử dụng")
