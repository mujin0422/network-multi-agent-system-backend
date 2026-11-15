"""HTTP contracts for identity authentication."""

from pydantic import BaseModel, Field

from app.domains.identity.schemas.user import User


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, description="Email của user.")
    password: str = Field(min_length=1, max_length=1024, repr=False, json_schema_extra={"writeOnly": True}, description="Password của user.")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512, description="Token để làm mới access token.")


class TokenResponse(BaseModel):
    access_token: str = Field(description="Access token JWT được cấp cho user.")
    refresh_token: str = Field(description="Refresh token được cấp cho user.")
    token_type: str = Field(default="bearer", description="Loại token.")
    expires_in: int = Field(description="Thời gian hết hạn của access token (giây).")
    user: User = Field(description="Thông tin user được xác thực.")


class AccessTokenPayload(BaseModel):
    sub: str = Field(description="ID user.")
    sid: str = Field(description="ID session.")
    exp: int = Field(description="Thời điểm hết hạn của access token (epoch seconds).")
    iat: int = Field(description="Thời điểm phát hành access token (epoch seconds).")
    jti: str = Field(description="ID duy nhất của access token (JWT ID).")
