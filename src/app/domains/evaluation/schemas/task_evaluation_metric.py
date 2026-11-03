"""Schema ánh xạ bảng ``task_evaluation_metrics``."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domains.evaluation.schemas.common import (
    EvaluationMetricType,
    EvaluationResult,
)


class TaskEvaluationMetric(BaseModel):
    """Một tiêu chí đánh giá độc lập thuộc Task Evaluation."""

    id: UUID = Field(description="UUID của metric result.")
    evaluation_id: UUID = Field(description="Evaluation sở hữu metric.")
    metric_type: EvaluationMetricType = Field(description="Loại metric.")
    result: EvaluationResult = Field(description="Kết quả chấm metric.")
    is_required: bool = Field(description="Metric có bắt buộc cho Task hay không.")
    was_attempted: bool | None = Field(
        default=None,
        description="Agent có thực hiện tiêu chí cần đánh giá hay không.",
    )
    expected_value: object | None = Field(
        default=None,
        description="Giá trị kỳ vọng dùng làm ground truth.",
    )
    actual_value: object | None = Field(
        default=None,
        description="Giá trị thực tế thu được từ quá trình thực thi.",
    )
    evidence: object | None = Field(
        default=None,
        description="Bằng chứng hỗ trợ cho kết quả đánh giá.",
    )
    created_at: datetime = Field(description="Thời điểm tạo metric theo UTC.")
