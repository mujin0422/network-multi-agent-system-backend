"""Schema ánh xạ bảng ``roles``."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    """Dữ liệu đầu vào khi tạo vai trò."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class RoleUpdate(BaseModel):
    """Các trường được phép sửa của vai trò."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class Role(BaseModel):
    """Vai trò hệ thống cùng metadata audit."""

    id: str = Field(description="Khóa chính của vai trò.")
    name: str = Field(max_length=100, description="Tên vai trò duy nhất.")
    description: str | None = Field(default=None, description="Mô tả vai trò.")
    created_by: str | None = Field(default=None, description="ID user tạo vai trò.")
    last_updated_by: str | None = Field(
        default=None,
        description="ID user cập nhật vai trò gần nhất.",
    )
    created_at: datetime = Field(description="Thời điểm tạo vai trò theo UTC.")
    last_updated_at: datetime | None = Field(
        default=None,
        description="Thời điểm cập nhật gần nhất theo UTC.",
    )
