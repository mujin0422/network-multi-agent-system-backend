"""Schema ánh xạ bảng ``brands``."""

from pydantic import BaseModel, Field


class Brand(BaseModel):
    """Hãng thiết bị và các Netmiko driver được hỗ trợ."""

    id: str = Field(description="Khóa chính của hãng thiết bị.")
    name: str = Field(max_length=100, description="Tên hãng duy nhất.")
    supported_drivers: list[str] = Field(
        default_factory=list,
        description="Danh sách Netmiko device_type hợp lệ, không trùng nhau.",
    )
