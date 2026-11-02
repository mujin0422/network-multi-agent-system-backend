"""SQLAlchemy model ánh xạ bảng benchmark_runs."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class BenchmarkRunModel(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("benchmark_scenarios.id"))
    scenario_version: Mapped[str] = mapped_column(String(30))
    scenario_name: Mapped[str] = mapped_column(String(100))
    scenario_snapshot: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    started_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    initial_message: Mapped[str] = mapped_column(Text)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey("conversations.id"))
    source_message_id: Mapped[str | None] = mapped_column(ForeignKey("messages.id"))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id"))
    evaluation_id: Mapped[UUID | None] = mapped_column(ForeignKey("task_evaluations.id"))
    evaluation_result: Mapped[str | None] = mapped_column(String(30))
    cleanup_required: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleaned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
