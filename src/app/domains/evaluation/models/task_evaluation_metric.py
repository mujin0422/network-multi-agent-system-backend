"""SQLAlchemy model ánh xạ bảng task_evaluation_metrics."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.evaluation.schemas import EvaluationMetricType, EvaluationResult


class TaskEvaluationMetricModel(Base):
    __tablename__ = "task_evaluation_metrics"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_id", "metric_type", name="uq_task_evaluation_metric_type"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("task_evaluations.id", ondelete="CASCADE")
    )
    metric_type: Mapped[EvaluationMetricType] = mapped_column(
        Enum(EvaluationMetricType, name="evaluation_metric_type")
    )
    result: Mapped[EvaluationResult] = mapped_column(
        Enum(EvaluationResult, name="evaluation_result")
    )
    is_required: Mapped[bool] = mapped_column(Boolean)
    was_attempted: Mapped[bool | None] = mapped_column(Boolean)
    expected_value: Mapped[object | None] = mapped_column(JSONB)
    actual_value: Mapped[object | None] = mapped_column(JSONB)
    evidence: Mapped[object | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
