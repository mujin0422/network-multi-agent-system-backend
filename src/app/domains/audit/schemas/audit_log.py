"""HTTP và service contracts của System Audit domain."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AuditActorType(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    AGENT = "AGENT"


class AuditEventStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    DENIED = "DENIED"


SENSITIVE_EVENT_KEYS = {
    "access_token",
    "authorization",
    "credential",
    "password",
    "password_hash",
    "refresh_token",
    "secret",
}


def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in SENSITIVE_EVENT_KEYS
            or _contains_sensitive_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


class AuditLogCreate(BaseModel):
    """Dữ liệu nội bộ dùng để ghi một audit log bất biến."""

    model_config = ConfigDict(str_strip_whitespace=True)

    actor_user_id: str | None = Field(
        default=None,
        max_length=64,
        description="ID user đã xác thực thực hiện hành động.",
    )
    actor_display_name: str | None = Field(
        default=None,
        max_length=255,
        description="Tên actor tại thời điểm ghi audit log.",
    )
    actor_type: AuditActorType = Field(description="Loại actor tạo sự kiện audit.")
    action: str = Field(
        min_length=1,
        max_length=100,
        description="Mã hành động ổn định ở dạng chữ hoa.",
    )
    resource_type: str = Field(
        min_length=1,
        max_length=100,
        description="Loại tài nguyên bị tác động.",
    )
    resource_id: str | None = Field(
        default=None,
        max_length=64,
        description="ID tài nguyên bị tác động nếu có.",
    )
    event_status: AuditEventStatus = Field(description="Kết quả của hành động audit.")
    summary: str | None = Field(default=None, description="Mô tả ngắn đã loại dữ liệu nhạy cảm.")
    event_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata JSON có cấu trúc và không chứa secret.",
    )
    request_id: UUID | None = Field(
        default=None,
        description="Correlation ID của request liên quan.",
    )
    source_ip: str | None = Field(
        default=None,
        max_length=45,
        description="Địa chỉ IPv4 hoặc IPv6 của client.",
    )
    user_agent: str | None = Field(
        default=None,
        description="User-Agent của client tạo request.",
    )

    @field_validator("action", "resource_type")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        """Chuẩn hóa mã hành động và tài nguyên để truy vấn nhất quán."""

        return value.strip().upper()

    @field_validator("event_data")
    @classmethod
    def reject_sensitive_event_data(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Ngăn dữ liệu xác thực nhạy cảm bị ghi vào audit metadata."""

        if _contains_sensitive_key(value):
            raise ValueError("event_data chứa trường dữ liệu nhạy cảm")
        return value

    @model_validator(mode="after")
    def validate_actor(self) -> "AuditLogCreate":
        """Bắt buộc sự kiện do USER tạo phải liên kết tới user đã xác thực."""

        if self.actor_type == AuditActorType.USER and not self.actor_user_id:
            raise ValueError("actor_user_id là bắt buộc khi actor_type là USER")
        return self


class AuditLog(AuditLogCreate):
    """Bản ghi audit công khai, chỉ đọc qua API."""

    id: UUID = Field(description="UUID duy nhất của audit log.")
    occurred_at: datetime = Field(description="Thời điểm sự kiện xảy ra theo UTC.")
