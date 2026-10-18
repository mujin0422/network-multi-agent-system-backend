"""Request và response schemas cho resource Brand."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrandPayload(BaseModel):
    """Các trường có thể nhập khi tạo hoặc cập nhật Brand."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, description="Tên hãng duy nhất.")
    supported_drivers: list[str] = Field(
        default_factory=list,
        description="Danh sách Netmiko device_type hợp lệ, không trùng nhau.",
    )
    @field_validator("supported_drivers")
    @classmethod
    def validate_supported_drivers(cls, drivers: list[str]) -> list[str]:
        """Loại khoảng trắng và từ chối driver rỗng hoặc trùng nhau."""

        normalized = [driver.strip() for driver in drivers]
        if any(not driver for driver in normalized):
            raise ValueError("Driver không được để trống")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Danh sách driver không được trùng nhau")
        return normalized


class BrandCreate(BrandPayload):
    """Payload thêm một hãng thiết bị mới."""


class BrandUpdate(BaseModel):
    """Payload sửa một phần Brand; trường không gửi sẽ được giữ nguyên."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Tên hãng mới.",
    )
    supported_drivers: list[str] | None = Field(
        default=None,
        description="Danh sách Netmiko device_type mới.",
    )

    @field_validator("supported_drivers")
    @classmethod
    def validate_supported_drivers(cls, drivers: list[str] | None) -> list[str] | None:
        """Áp dụng cùng quy tắc driver như payload tạo mới."""

        if drivers is None:
            return None
        return BrandPayload.validate_supported_drivers(drivers)


class Brand(BaseModel):
    """Hãng thiết bị và các Netmiko driver được hỗ trợ."""

    id: str = Field(description="Khóa chính của hãng thiết bị.")
    name: str = Field(max_length=100, description="Tên hãng duy nhất.")
    supported_drivers: list[str] = Field(
        default_factory=list,
        description="Danh sách Netmiko device_type hợp lệ, không trùng nhau.",
    )
