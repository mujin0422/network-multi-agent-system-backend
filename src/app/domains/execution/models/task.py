"""SQLAlchemy model ánh xạ bảng tasks."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import TaskStatus, TaskType


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    source_message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    input_message: Mapped[str] = mapped_column(Text)
    task_status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"))
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType, name="task_type"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
