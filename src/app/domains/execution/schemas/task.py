"""Task contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.domains.execution.schemas.operation import Operation


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class TaskType(StrEnum):
    UNCLASSIFIED = "UNCLASSIFIED"
    INFORMATION_RETRIEVAL = "INFORMATION_RETRIEVAL"
    DIAGNOSIS = "DIAGNOSIS"
    CONFIGURATION = "CONFIGURATION"
    REMEDIATION = "REMEDIATION"
    COMPOSITE = "COMPOSITE"


class TaskCreate(BaseModel):
    """Payload tạo Task từ một USER message."""

    model_config = ConfigDict(str_strip_whitespace=True)

    conversation_id: str = Field(min_length=1, description="ID conversation nguồn.")
    source_message_id: str = Field(min_length=1, description="ID USER message nguồn.")
    user_id: str = Field(min_length=1, description="ID owner của conversation.")
    input_message: str = Field(min_length=1, description="Nội dung nguyên bản của message.")


class Task(BaseModel):
    """Bản ghi tương ứng bảng ``tasks``."""

    id: str = Field(description="Khóa chính của Task.")
    conversation_id: str = Field(description="ID conversation nguồn.")
    source_message_id: str = Field(description="ID USER message duy nhất sinh Task.")
    user_id: str = Field(description="ID user sở hữu Task.")
    input_message: str = Field(description="Nội dung message nguồn không thay đổi.")
    task_status: TaskStatus = Field(description="Trạng thái end-to-end của Task.")
    task_type: TaskType = Field(
        default=TaskType.UNCLASSIFIED,
        description="Loại mục tiêu của Task.",
    )
    started_at: datetime | None = Field(default=None, description="Thời điểm bắt đầu.")
    completed_at: datetime | None = Field(default=None, description="Thời điểm kết thúc.")
    created_at: datetime = Field(description="Thời điểm tạo Task theo UTC.")


class TaskDetail(Task):
    """Task response mở rộng kèm execution plan."""

    operations: list[Operation] = Field(
        default_factory=list,
        description="Các operation được sắp theo display_order.",
    )
