"""SQLAlchemy model ánh xạ bảng device_action_logs."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import (
    DeviceActionPhase,
    DeviceActionStatus,
    DeviceActionType,
)


class DeviceActionLogModel(Base):
    __tablename__ = "device_action_logs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    operation_id: Mapped[str] = mapped_column(ForeignKey("task_operations.id"))
    operation_device_id: Mapped[str] = mapped_column(
        ForeignKey("task_operation_devices.id")
    )
    execution_id: Mapped[str] = mapped_column(ForeignKey("task_executions.id"))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    rollback_of_action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("device_action_logs.id")
    )
    action_type: Mapped[DeviceActionType] = mapped_column(
        Enum(DeviceActionType, name="device_action_type")
    )
    action_phase: Mapped[DeviceActionPhase] = mapped_column(
        Enum(DeviceActionPhase, name="device_action_phase")
    )
    sequence_number: Mapped[int] = mapped_column(Integer)
    command: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    action_log_status: Mapped[DeviceActionStatus] = mapped_column(
        Enum(DeviceActionStatus, name="device_action_status")
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
