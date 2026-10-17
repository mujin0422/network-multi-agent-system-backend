"""Schema ánh xạ bảng ``management_functions``."""

from pydantic import BaseModel, Field


class ManagementFunction(BaseModel):
    """Chức năng quản trị được sử dụng khi xây dựng permission."""

    id: str = Field(description="Khóa chính của chức năng.")
    name: str = Field(max_length=100, description="Tên chức năng duy nhất.")
    description: str | None = Field(default=None, description="Mô tả chức năng.")
