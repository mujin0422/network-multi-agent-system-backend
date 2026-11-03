"""SQLAlchemy model ánh xạ bảng task_evaluations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.evaluation.schemas import EvaluationStatus, EvaluatorType


class TaskEvaluationModel(Base):
    __tablename__ = "task_evaluations"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), unique=True)
    evaluation_status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus, name="evaluation_status"))
    evaluator_type: Mapped[EvaluatorType] = mapped_column(Enum(EvaluatorType, name="evaluator_type"))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
