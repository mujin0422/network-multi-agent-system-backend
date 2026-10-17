"""Schema ánh xạ bảng ``actions``."""

from pydantic import BaseModel, Field


class Action(BaseModel):
    """Hành động có thể được cấp quyền trên một chức năng."""

    id: str = Field(description="Khóa chính của hành động.")
    name: str = Field(max_length=50, description="Tên hành động duy nhất.")
    description: str | None = Field(default=None, description="Mô tả hành động.")
