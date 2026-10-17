"""Schema ánh xạ bảng ``categories``."""

from pydantic import BaseModel, Field


class Category(BaseModel):
    """Loại thiết bị như Router, Switch hoặc Firewall."""

    id: str = Field(description="Khóa chính của category.")
    name: str = Field(max_length=100, description="Tên category duy nhất.")
