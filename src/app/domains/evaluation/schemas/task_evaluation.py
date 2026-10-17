"""Schema ánh xạ bảng ``task_evaluations``."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.evaluation.schemas.status import (
    EvaluationResult,
    EvaluationStatus,
    EvaluatorType,
)


class TaskEvaluation(BaseModel):
    """Kết quả goal, RCA, remediation và safety của một Task kết thúc."""

    id: UUID = Field(description="UUID của evaluation.")
    task_id: str = Field(description="ID Task duy nhất được đánh giá.")
    evaluation_status: EvaluationStatus = Field(description="Trạng thái workflow.")
    expected_outcome: Any | None = Field(
        default=None,
        description="JSONB mô tả kết quả mong đợi.",
    )
    actual_outcome: Any | None = Field(
        default=None,
        description="JSONB mô tả kết quả quan sát thực tế.",
    )
    goal_result: EvaluationResult = Field(description="Kết quả đạt mục tiêu.")
    expected_root_cause: Any | None = Field(
        default=None,
        description="JSONB root cause kỳ vọng của benchmark.",
    )
    predicted_root_cause: Any | None = Field(
        default=None,
        description="JSONB root cause do hệ thống dự đoán.",
    )
    rca_result: EvaluationResult = Field(description="Kết quả đánh giá RCA.")
    remediation_required: bool = Field(description="Task có cần remediation không.")
    remediation_attempted: bool = Field(description="Đã thử remediation hay chưa.")
    remediation_result: EvaluationResult = Field(
        description="Kết quả remediation hoặc NOT_APPLICABLE.",
    )
    safety_result: EvaluationResult = Field(description="Kết quả đánh giá an toàn.")
    evaluation_evidence: Any | None = Field(
        default=None,
        description="JSONB evidence hỗ trợ kết luận evaluation.",
    )
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
