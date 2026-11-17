"""Contract công khai cho Task activity truyền qua SSE."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domains.execution.schemas.task_activity_event import ActivityEventType


class TaskStreamEvent(BaseModel):
    """Event SSE có sequence để client replay sau khi mất kết nối."""

    event_id: str = Field(description="Sequence dùng làm SSE event ID.")
    event_type: ActivityEventType = Field(description="Loại activity của Task.")
    task_id: str = Field(description="Task sở hữu event.")
    sequence_number: int = Field(gt=0, description="Thứ tự event trong Task.")
    occurred_at: datetime = Field(description="Thời điểm event được ghi nhận.")
    data: dict[str, Any] = Field(description="TaskActivityEvent đầy đủ.")
