"""Enum contracts owned by the Evaluation domain."""

from enum import StrEnum


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
