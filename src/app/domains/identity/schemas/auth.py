"""HTTP contracts for identity authentication."""

from pydantic import BaseModel, Field

from app.domains.identity.schemas.user import User


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class AccessTokenPayload(BaseModel):
    sub: str
    sid: str
    exp: int
    iat: int
    jti: str
