"""SQLAlchemy model ánh xạ bảng task_operation_devices."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import AccessMode, DeviceRole, OperationDeviceStatus


class TaskOperationDeviceModel(Base):
    __tablename__ = "task_operation_devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation_id: Mapped[str] = mapped_column(ForeignKey("task_operations.id"))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    operation_device_status: Mapped[OperationDeviceStatus] = mapped_column(Enum(OperationDeviceStatus, name="operation_device_status"))
    device_role: Mapped[DeviceRole] = mapped_column(Enum(DeviceRole, name="device_role"))
    access_mode: Mapped[AccessMode] = mapped_column(Enum(AccessMode, name="access_mode"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
