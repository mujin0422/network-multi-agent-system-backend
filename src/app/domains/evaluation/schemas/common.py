"""Enum dùng chung cho hai bảng Evaluation."""

from enum import StrEnum


class EvaluationStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class EvaluationResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvaluatorType(StrEnum):
    AUTOMATED = "AUTOMATED"
    HUMAN = "HUMAN"


class EvaluationMetricType(StrEnum):
    GOAL = "GOAL"
    RCA = "RCA"
    REMEDIATION = "REMEDIATION"
    SAFETY = "SAFETY"
    LATENCY = "LATENCY"
    INTERACTION_TURNS = "INTERACTION_TURNS"
