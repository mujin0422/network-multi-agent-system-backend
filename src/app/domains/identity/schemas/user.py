"""Schemas ánh xạ bảng ``users``."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.domains.identity.schemas.status import UserStatus


class User(BaseModel):
    """Thông tin tài khoản an toàn để trả qua API."""

    id: str = Field(description="Khóa chính của user.")
    role_id: str = Field(description="ID role hiện tại của user.")
    email: str = Field(
        max_length=255,
        pattern=r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$",
        description="Email đăng nhập duy nhất, viết thường.",
    )
    full_name: str = Field(max_length=255, description="Tên hiển thị của user.")
    user_status: UserStatus = Field(description="Trạng thái tài khoản.")
    created_at: datetime = Field(description="Thời điểm tạo tài khoản theo UTC.")
    last_updated_at: datetime | None = Field(
        default=None,
        description="Thời điểm cập nhật tài khoản gần nhất.",
    )
    last_login_at: datetime | None = Field(
        default=None,
        description="Thời điểm đăng nhập thành công gần nhất.",
    )


class UserRecord(User):
    """Bản ghi nội bộ đầy đủ; password hash không được serialize ra response."""

    password_hash: str = Field(
        exclude=True,
        repr=False,
        description="Bcrypt password hash chỉ dùng trong authentication.",
    )
