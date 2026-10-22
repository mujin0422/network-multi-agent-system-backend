"""Schema ánh xạ bảng ``task_activity_events``."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ActivityActorType(StrEnum):
    ORCHESTRATOR = "ORCHESTRATOR"
    PLANNER = "PLANNER"
    NETWORK = "NETWORK"
    ANALYST = "ANALYST"
    TOOL = "TOOL"


class ActivityEventType(StrEnum):
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    TASK_CREATED = "TASK_CREATED"
    PLAN_GENERATED = "PLAN_GENERATED"
    OPERATIONS_CREATED = "OPERATIONS_CREATED"
    DEPENDENCIES_CREATED = "DEPENDENCIES_CREATED"
    DEVICES_ASSIGNED = "DEVICES_ASSIGNED"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    COMMAND_EXECUTED = "COMMAND_EXECUTED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_APPROVED = "APPROVAL_APPROVED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    FINAL_RESPONSE_CREATED = "FINAL_RESPONSE_CREATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"


class ActivityEventStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TaskActivityEvent(BaseModel):
    """Một mốc có thứ tự trong timeline xử lý của Task."""

    id: str = Field(description="Khóa chính của activity event.")
    task_id: str = Field(description="ID Task sở hữu timeline event.")
    operation_id: str | None = Field(default=None, description="ID Operation liên quan.")
    execution_id: str | None = Field(default=None, description="ID Execution liên quan.")
    actor_type: ActivityActorType = Field(description="Thành phần tạo event.")
    event_type: ActivityEventType = Field(description="Loại event nghiệp vụ.")
    event_status: ActivityEventStatus = Field(description="Trạng thái event.")
    sequence_number: int = Field(gt=0, description="Thứ tự event trong Task.")
    event_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Dữ liệu có cấu trúc phục vụ Chat UI.",
    )
    started_at: datetime | None = Field(default=None, description="Thời điểm bắt đầu.")
    completed_at: datetime | None = Field(default=None, description="Thời điểm kết thúc.")
    created_at: datetime = Field(description="Thời điểm tạo event.")
