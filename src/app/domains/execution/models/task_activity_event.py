"""SQLAlchemy model ánh xạ bảng task_activity_events."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import ActivityActorType, ActivityEventStatus, ActivityEventType


class TaskActivityEventModel(Base):
    __tablename__ = "task_activity_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    operation_id: Mapped[str | None] = mapped_column(ForeignKey("task_operations.id"))
    execution_id: Mapped[str | None] = mapped_column(ForeignKey("task_executions.id"))
    actor_type: Mapped[ActivityActorType] = mapped_column(Enum(ActivityActorType, name="activity_actor_type"), nullable=False)
    event_type: Mapped[ActivityEventType] = mapped_column(Enum(ActivityEventType, name="activity_event_type"), nullable=False)
    event_status: Mapped[ActivityEventStatus] = mapped_column(Enum(ActivityEventStatus, name="activity_event_status"), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
