"""Read-only Task evaluation endpoints; never expose benchmark ground truth before completion."""

from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.config import get_settings
from app.domains.evaluation.repositories import TaskEvaluationRepository
from app.domains.evaluation.schemas import TaskEvaluationDetail, TaskEvaluationSummary
from app.domains.execution.routers.dependencies import get_execution_service
from app.domains.execution.services import ExecutionService
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User

router = APIRouter()


@lru_cache
def _evaluation_repository() -> TaskEvaluationRepository:
    return TaskEvaluationRepository(get_settings().database_url)


@router.get("", response_model=list[TaskEvaluationSummary])
async def list_evaluations(
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    evaluation_repository: Annotated[TaskEvaluationRepository, Depends(_evaluation_repository)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[TaskEvaluationSummary]:
    """Lịch sử đánh giá, chỉ có trạng thái metric; không trả ground truth."""

    return evaluation_repository.get_recent(limit)


@router.get("/tasks/{task_id}", response_model=TaskEvaluationDetail | None)
async def get_task_evaluation(
    task_id: str,
    execution_service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    evaluation_repository: Annotated[TaskEvaluationRepository, Depends(_evaluation_repository)],
) -> TaskEvaluationDetail | None:
    """Task must exist. Null means no persisted evaluation, not a FAIL result."""

    execution_service.get_task(task_id)
    return evaluation_repository.get_by_task_id(task_id)
