"""Schema ánh xạ bảng ``device_action_logs``."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.execution.schemas.status import (
    DeviceActionPhase,
    DeviceActionStatus,
    DeviceActionType,
)


class DeviceActionLog(BaseModel):
    """Audit bất biến cho command thực tế đã gửi xuống thiết bị."""

    id: UUID = Field(description="UUID của audit log.")
    task_id: str = Field(description="ID Task chứa command.")
    operation_id: str = Field(description="ID Operation chứa command.")
    operation_device_id: str = Field(description="ID mapping operation-device.")
    execution_id: str = Field(description="ID execution đã gửi command.")
    device_id: str = Field(description="ID thiết bị nhận command.")
    rollback_of_action_id: UUID | None = Field(
        default=None,
        description="Action gốc được rollback; null nếu không phải rollback.",
    )
    action_type: DeviceActionType = Field(description="Loại audit READ hoặc WRITE.")
    action_phase: DeviceActionPhase = Field(description="Giai đoạn chi tiết của action.")
    sequence_number: int = Field(gt=0, description="Thứ tự command trong execution.")
    command: str = Field(min_length=1, description="Command thực tế gửi xuống device.")
    result: str | None = Field(default=None, description="Kết quả trả về từ thiết bị.")
    action_log_status: DeviceActionStatus = Field(description="Kết quả command.")
    error_message: str | None = Field(
        default=None,
        description="Chi tiết lỗi; bắt buộc khi FAILED.",
    )
    executed_at: datetime = Field(description="Thời điểm gửi command theo UTC.")
