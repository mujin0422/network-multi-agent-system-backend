"""SQLAlchemy model ánh xạ bảng task_executions."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import ExecutionStatus


class TaskExecutionModel(Base):
    __tablename__ = "task_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    operation_id: Mapped[str | None] = mapped_column(ForeignKey("task_operations.id"))
    operation_device_id: Mapped[str | None] = mapped_column(ForeignKey("task_operation_devices.id"))
    agent_name: Mapped[str] = mapped_column(String(100))
    tool_name: Mapped[str | None] = mapped_column(String(100))
    step_order: Mapped[int] = mapped_column(Integer)
    input: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    output: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    execution_status: Mapped[ExecutionStatus] = mapped_column(Enum(ExecutionStatus, name="execution_status"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
