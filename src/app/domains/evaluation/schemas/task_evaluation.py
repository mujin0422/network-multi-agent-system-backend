"""Schema ánh xạ bảng ``task_evaluations``."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationStatus(StrEnum):
    """Trạng thái workflow của một evaluation."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class EvaluationResult(StrEnum):
    """Kết quả đánh giá goal, RCA, remediation hoặc safety."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvaluatorType(StrEnum):
    """Nguồn thực hiện evaluation."""

    AUTOMATED = "AUTOMATED"
    HUMAN = "HUMAN"


class EvaluationMetricType(StrEnum):
    """Loại tiêu chí được chấm trong một evaluation."""

    GOAL = "GOAL"
    RCA = "RCA"
    REMEDIATION = "REMEDIATION"
    SAFETY = "SAFETY"


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
class TaskEvaluationMetric(BaseModel):
    """Một tiêu chí đánh giá độc lập thuộc Task Evaluation."""

    id: UUID = Field(description="UUID của metric result.")
    evaluation_id: UUID = Field(description="Evaluation sở hữu metric.")
    metric_type: EvaluationMetricType = Field(description="Loại metric.")
    result: EvaluationResult = Field(description="Kết quả chấm metric.")
    is_required: bool = Field(description="Metric có bắt buộc cho Task hay không.")
    was_attempted: bool | None = Field(
        default=None,
        description="Đã thử thực hiện hay chưa; chủ yếu dùng cho remediation.",
    )
    expected_value: object | None = Field(
        default=None,
        description="Giá trị hoặc điều kiện mong đợi dạng JSONB.",
    )
    actual_value: object | None = Field(
        default=None,
        description="Giá trị quan sát hoặc dự đoán thực tế dạng JSONB.",
    )
    evidence: object | None = Field(
        default=None,
        description="Bằng chứng có cấu trúc hỗ trợ kết luận.",
    )
    created_at: datetime = Field(description="Thời điểm tạo metric theo UTC.")


class TaskEvaluationDetail(TaskEvaluation):
    """Evaluation kèm các metric dùng tại service/repository boundary."""

    metrics: list[TaskEvaluationMetric] = Field(
        default_factory=list,
        description="Các kết quả GOAL, RCA, REMEDIATION và SAFETY.",
    )


class TaskEvaluationSummary(TaskEvaluation):
    """Compact evaluation row for the history page (no ground truth or evidence)."""

    results: dict[EvaluationMetricType, EvaluationResult] = Field(
        default_factory=dict,
        description="Chỉ trạng thái từng metric; dữ liệu chi tiết lấy từ API theo Task.",
    )
