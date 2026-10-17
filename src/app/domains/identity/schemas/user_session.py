"""Schema ánh xạ bảng ``user_sessions``."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserSessionRecord(BaseModel):
    """Phiên đăng nhập nội bộ; refresh token chỉ được lưu dưới dạng hash."""

    id: UUID = Field(description="UUID của phiên đăng nhập.")
    user_id: str = Field(description="ID user sở hữu phiên.")
    refresh_token_hash: str = Field(
        exclude=True,
        repr=False,
        description="Hash refresh token; không trả ra public API.",
    )
    expires_at: datetime = Field(description="Thời điểm phiên hết hạn theo UTC.")
    created_at: datetime = Field(description="Thời điểm tạo phiên theo UTC.")
    revoked_at: datetime | None = Field(
        default=None,
        description="Thời điểm thu hồi phiên; null nếu phiên còn hiệu lực.",
    )
