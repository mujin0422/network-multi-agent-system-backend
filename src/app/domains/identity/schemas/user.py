"""Schemas ánh xạ bảng ``users``."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserStatus(StrEnum):
    """Trạng thái hoạt động của tài khoản người dùng."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class UserCreate(BaseModel):
    """Dữ liệu đầu vào khi tạo tài khoản."""

    model_config = ConfigDict(str_strip_whitespace=True)

    role_id: str = Field(min_length=1, description="ID vai trò được gán cho user.")
    email: str = Field(
        max_length=255,
        pattern=r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$",
        description="Email đăng nhập duy nhất.",
    )
    password: str = Field(
        min_length=8,
        max_length=1024,
        repr=False,
        json_schema_extra={"writeOnly": True},
        description="Mật khẩu thô; chỉ dùng để tạo password hash.",
    )
    full_name: str = Field(min_length=1, max_length=255)
    user_status: UserStatus = UserStatus.ACTIVE

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class UserUpdate(BaseModel):
    """Các trường được phép sửa của tài khoản."""

    model_config = ConfigDict(str_strip_whitespace=True)

    role_id: str | None = Field(default=None, min_length=1)
    email: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$",
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=1024,
        repr=False,
        json_schema_extra={"writeOnly": True},
    )
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    user_status: UserStatus | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


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
