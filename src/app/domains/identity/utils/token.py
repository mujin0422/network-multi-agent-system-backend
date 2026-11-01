"""Các hàm phát hành access token và refresh session của Identity domain."""

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import Settings
from app.domains.identity.schemas import (
    TokenResponse,
    User,
    UserSessionRecord,
)
from app.domains.identity.utils.security import hash_refresh_token


@dataclass(frozen=True, slots=True)
class IssuedTokenBundle:
    """Gói token trả cho client và session tương ứng để lưu database."""

    response: TokenResponse
    session: UserSessionRecord


def issue_token_bundle(
    user: User,
    issued_at: datetime,
    session_id: UUID,
    settings: Settings,
) -> IssuedTokenBundle:
    """Phát hành token pair và dựng session từ cùng một session ID."""

    raw_refresh = secrets.token_urlsafe(48)
    refresh_expires_at = issued_at + timedelta(
        days=settings.auth_refresh_token_days
    )
    access_expires_at = issued_at + timedelta(
        minutes=settings.auth_access_token_minutes
    )
    access_token = jwt.encode(
        {
            "sub": user.id,
            "sid": str(session_id),
            "iat": issued_at,
            "exp": access_expires_at,
            "jti": secrets.token_urlsafe(12),
        },
        settings.auth_jwt_secret,
        algorithm="HS256",
    )
    session = UserSessionRecord(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(raw_refresh),
        expires_at=refresh_expires_at,
        created_at=issued_at,
    )
    response = TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.auth_access_token_minutes * 60,
        user=User.model_validate(user.model_dump()),
    )
    return IssuedTokenBundle(response=response, session=session)
