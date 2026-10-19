"""Operation contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OperationStatus(StrEnum):
    PENDING = "PENDING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class OperationCreate(BaseModel):
    """Payload tạo một logical operation trong execution plan."""

    model_config = ConfigDict(str_strip_whitespace=True)

    operation_intent: str = Field(
        min_length=1,
        max_length=100,
        description="Intent logic do Planner tạo.",
    )
    display_order: int = Field(ge=1, description="Thứ tự operation trong Task.")
    operation_parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Tham số JSON object của operation.",
    )


class Operation(BaseModel):
    """Bản ghi tương ứng bảng ``task_operations``."""

    id: str = Field(description="Khóa chính của operation.")
    task_id: str = Field(description="ID Task sở hữu operation.")
    operation_intent: str = Field(description="Intent logic của operation.")
    display_order: int = Field(ge=1, description="Thứ tự operation trong Task.")
    operation_status: OperationStatus = Field(description="Trạng thái operation.")
    operation_parameters: dict[str, Any] = Field(description="Tham số JSON object.")
    created_at: datetime = Field(description="Thời điểm tạo theo UTC.")
    started_at: datetime | None = Field(default=None, description="Thời điểm bắt đầu.")
    completed_at: datetime | None = Field(default=None, description="Thời điểm kết thúc.")
