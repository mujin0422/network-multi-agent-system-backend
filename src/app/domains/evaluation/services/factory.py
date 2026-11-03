"""Composition factory cho TaskEvaluationService."""

from app.domains.evaluation.repositories import (
    TaskEvaluationMetricRepository,
    TaskEvaluationRepository,
)
from app.domains.evaluation.services.task_evaluation import TaskEvaluationService


def build_task_evaluation_service(database_url: str) -> TaskEvaluationService:
    """Khởi tạo service với repository chuyên trách cho từng bảng."""

    return TaskEvaluationService(
        TaskEvaluationRepository(database_url),
        TaskEvaluationMetricRepository(database_url),
    )
