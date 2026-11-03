"""Schema ánh xạ bảng ``task_evaluations``."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.evaluation.schemas.common import (
    EvaluationMetricType,
    EvaluationResult,
    EvaluationStatus,
    EvaluatorType,
)
from app.domains.evaluation.schemas.task_evaluation_metric import (
    TaskEvaluationMetric,
)


class TaskEvaluation(BaseModel):
    """Vòng đời và thông tin evaluator của một Task."""

    id: UUID = Field(description="UUID của evaluation.")
    task_id: str = Field(description="ID Task duy nhất được đánh giá.")
    evaluation_status: EvaluationStatus = Field(description="Trạng thái workflow.")
    evaluator_type: EvaluatorType = Field(description="AUTOMATED hoặc HUMAN.")
    evaluator_version: str | None = Field(
        default=None,
        max_length=100,
        description="Version evaluator/model/rubric.",
    )
    created_at: datetime = Field(description="Thời điểm tạo evaluation theo UTC.")
    evaluated_at: datetime | None = Field(
        default=None,
        description="Thời điểm evaluation hoàn tất hoặc lỗi.",
    )


class TaskEvaluationDetail(TaskEvaluation):
    """Evaluation kèm các metric dùng tại tầng service."""

    metrics: list[TaskEvaluationMetric] = Field(
        default_factory=list,
        description="Kết quả phân loại và các số đo benchmark.",
    )


class TaskEvaluationSummary(TaskEvaluation):
    """Compact evaluation row for the history page (no ground truth or evidence)."""

    results: dict[EvaluationMetricType, EvaluationResult] = Field(
        default_factory=dict,
        description="Trạng thái từng tiêu chí định tính.",
    )
    measurements: dict[EvaluationMetricType, int] = Field(
        default_factory=dict,
        description="Số đo định lượng LATENCY (ms) và INTERACTION_TURNS (lượt gọi tool).",
    )
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="Versioned structured RCA F1 scores (v4), omitted for legacy evaluators.",
    )

