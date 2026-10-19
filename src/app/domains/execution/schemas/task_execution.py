"""Schema ánh xạ bảng ``task_executions``."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class TaskExecution(BaseModel):
    """Một lần Agent hoặc Tool thực thi một bước của Task."""

    id: str = Field(description="Khóa chính của execution attempt.")
    task_id: str = Field(description="ID Task được thực thi.")
    operation_id: str | None = Field(default=None, description="ID Operation liên quan.")
    operation_device_id: str | None = Field(
        default=None,
        description="ID operation-device khi execution gắn với thiết bị.",
    )
    agent_name: str = Field(max_length=100, description="Tên Agent thực thi.")
    tool_name: str | None = Field(
        default=None,
        max_length=100,
        description="Tên Tool được Agent gọi; null nếu không dùng Tool.",
    )
    step_order: int = Field(gt=0, description="Thứ tự bước trong Task.")
    input: Any | None = Field(default=None, description="JSONB input đã loại secret.")
    output: Any | None = Field(default=None, description="JSONB output đã loại secret.")
    execution_status: ExecutionStatus = Field(description="Trạng thái execution.")
    error_message: str | None = Field(
        default=None,
        description="Chi tiết lỗi; bắt buộc khi FAILED.",
    )
    started_at: datetime | None = Field(default=None, description="Thời điểm bắt đầu.")
    completed_at: datetime | None = Field(default=None, description="Thời điểm kết thúc.")
    duration_ms: int | None = Field(
        default=None,
        ge=0,
        description="Thời lượng thực thi tính bằng millisecond.",
    )
    created_at: datetime = Field(description="Thời điểm tạo execution theo UTC.")
