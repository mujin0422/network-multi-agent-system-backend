"""Authentication and role permission use cases."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import Settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.utils import generate_uuid
from app.domains.identity.repositories import IdentityRepositoryProtocol
from app.domains.identity.schemas import (
    AccessTokenPayload,
    TokenResponse,
    User,
    UserSessionRecord,
    UserStatus,
)
from app.domains.identity.utils import (
    hash_refresh_token,
    verify_password,
)


class IdentityService:
    def __init__(
        self,
        repository: IdentityRepositoryProtocol,
        settings: Settings,
    ) -> None:
        self._repository = repository
        self._settings = settings

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
