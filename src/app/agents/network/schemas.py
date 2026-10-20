"""Kết quả thực thi có cấu trúc của Network Agent."""

from enum import StrEnum

from pydantic import BaseModel, Field

from app.domains.execution.schemas import AccessMode
from app.tools import CommandResult


# Trạng thái thực thi của Network Agent
class NetworkExecutionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


# Kết quả thực thi của Network Agent, bao gồm trạng thái, kết quả và thông báo lỗi nếu có.
class NetworkExecutionResult(BaseModel):
    operation_id: str
    operation_device_id: str
    device_id: str
    access_mode: AccessMode
    status: NetworkExecutionStatus
    results: list[CommandResult] = Field(default_factory=list)
    error_message: str | None = None
