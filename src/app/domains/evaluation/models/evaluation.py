"""SQLAlchemy model owned by the Evaluation domain."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.evaluation.schemas import EvaluationResult, EvaluationStatus, EvaluatorType


class TaskEvaluationModel(Base):
    __tablename__ = "task_evaluations"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), unique=True)
    evaluation_status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus, name="evaluation_status"))
    expected_outcome: Mapped[object | None] = mapped_column(JSONB)
    actual_outcome: Mapped[object | None] = mapped_column(JSONB)
    goal_result: Mapped[EvaluationResult] = mapped_column(Enum(EvaluationResult, name="evaluation_result"))
    expected_root_cause: Mapped[object | None] = mapped_column(JSONB)
    predicted_root_cause: Mapped[object | None] = mapped_column(JSONB)
    rca_result: Mapped[EvaluationResult] = mapped_column(Enum(EvaluationResult, name="evaluation_result"))
    remediation_required: Mapped[bool] = mapped_column(Boolean)
    remediation_attempted: Mapped[bool] = mapped_column(Boolean)
    remediation_result: Mapped[EvaluationResult] = mapped_column(Enum(EvaluationResult, name="evaluation_result"))
    safety_result: Mapped[EvaluationResult] = mapped_column(Enum(EvaluationResult, name="evaluation_result"))
    evaluation_evidence: Mapped[object | None] = mapped_column(JSONB)
    evaluator_type: Mapped[EvaluatorType] = mapped_column(Enum(EvaluatorType, name="evaluator_type"))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
