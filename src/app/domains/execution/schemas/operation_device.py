"""Schema ánh xạ bảng ``task_operation_devices``."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OperationDeviceStatus(StrEnum):
    PENDING = "PENDING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class DeviceRole(StrEnum):
    SOURCE = "SOURCE"
    TARGET = "TARGET"
    CONTEXT = "CONTEXT"


class AccessMode(StrEnum):
    READ = "READ"
    WRITE = "WRITE"


class TaskOperationDevice(BaseModel):
    """Thiết bị tham gia một operation cùng role và access mode."""

    id: str = Field(description="Khóa chính của operation-device mapping.")
    operation_id: str = Field(description="ID operation sở hữu mapping.")
    device_id: str = Field(description="ID device tham gia operation.")
    operation_device_status: OperationDeviceStatus = Field(
        description="Trạng thái thực thi trên riêng thiết bị này.",
    )
    device_role: DeviceRole = Field(description="Vai trò SOURCE, TARGET hoặc CONTEXT.")
    access_mode: AccessMode = Field(description="Quyền READ hoặc WRITE trên thiết bị.")
    error_message: str | None = Field(
        default=None,
        description="Chi tiết lỗi; bắt buộc khi trạng thái FAILED.",
    )
    started_at: datetime | None = Field(default=None, description="Thời điểm bắt đầu.")
    completed_at: datetime | None = Field(
        default=None,
        description="Thời điểm kết thúc.",
    )
