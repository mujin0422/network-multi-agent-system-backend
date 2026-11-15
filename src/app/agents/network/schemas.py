"""Kết quả thực thi có cấu trúc của Network Agent."""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.domains.execution.schemas import AccessMode
from app.tools import CommandResult


class NetworkExecutionStatus(StrEnum):
    """Trạng thái thực thi của Network Agent."""
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class NetworkExecutionResult(BaseModel):
    """Kết quả thực thi của Network Agent, bao gồm trạng thái, kết quả và thông báo lỗi nếu có."""
    operation_id: str = Field(description="ID của operation đang thực thi.")
    operation_device_id: str = Field(description="ID của thiết bị đang thực thi operation.")
    device_id: str = Field(description="ID của thiết bị mạng.")
    access_mode: AccessMode = Field(description="Chế độ truy cập thiết bị.")
    status: NetworkExecutionStatus = Field(description="Trạng thái thực thi.")
    results: list[CommandResult] = Field(default_factory=list, description="Danh sách kết quả thực thi các lệnh.")
    error_message: str | None = Field(default=None, description="Thông báo lỗi nếu có.")