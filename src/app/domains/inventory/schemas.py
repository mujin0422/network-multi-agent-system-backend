"""Contracts thuộc Network Inventory domain."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeviceCreate(BaseModel):
    """Dữ liệu frontend cần gửi khi đăng ký một thiết bị."""

    model_config = ConfigDict(str_strip_whitespace=True)

    credential_id: str | None = None
    brand_id: str = Field(min_length=1)
    category_id: str = Field(min_length=1)
    hostname: str = Field(min_length=1, max_length=255)
    host: str = Field(default="127.0.0.1", min_length=1)
    port: int = Field(gt=0, le=65535)
    device_type: str = Field(default="cisco_ios_telnet", min_length=1)
    location: str | None = None
    last_updated_by: str = Field(min_length=1)


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    credential_id: str | None = None
    brand_id: str | None = Field(default=None, min_length=1)
    category_id: str | None = Field(default=None, min_length=1)
    hostname: str | None = Field(default=None, min_length=1, max_length=255)
    host: str | None = Field(default=None, min_length=1)
    port: int | None = Field(default=None, gt=0, le=65535)
    device_type: str | None = Field(default=None, min_length=1)
    location: str | None = None
    last_updated_by: str = Field(min_length=1)


class Device(BaseModel):
    id: str
    credential_id: str | None
    brand_id: str
    category_id: str
    hostname: str
    host: str
    port: int
    device_type: str
    location: str | None
    last_updated_by: str
    created_at: datetime
    last_updated_at: datetime
