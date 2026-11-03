"""Dependency composition cho Evaluation domain."""

from functools import lru_cache

from app.core.config import get_settings
from app.domains.evaluation.services import (
    TaskEvaluationService,
    build_task_evaluation_service as create_task_evaluation_service,
)


@lru_cache
def _build_task_evaluation_service() -> TaskEvaluationService:
    return create_task_evaluation_service(get_settings().database_url)


async def get_task_evaluation_service() -> TaskEvaluationService:
    return _build_task_evaluation_service()
