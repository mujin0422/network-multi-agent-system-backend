"""Read-only Task evaluation endpoints; never expose benchmark ground truth before completion."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.pagination import PageResponse
from app.domains.evaluation.routers.dependencies import get_task_evaluation_service
from app.domains.evaluation.schemas import TaskEvaluationDetail, TaskEvaluationSummary
from app.domains.evaluation.services import TaskEvaluationService
from app.domains.execution.routers.dependencies import get_execution_service
from app.domains.execution.services import ExecutionService
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User

router = APIRouter()


@router.get("", response_model=list[TaskEvaluationSummary])
def list_evaluations(
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    evaluation_service: Annotated[
        TaskEvaluationService,
        Depends(get_task_evaluation_service),
    ],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[TaskEvaluationSummary]:
    """Lịch sử đánh giá, chỉ có trạng thái metric; không trả ground truth."""

    return evaluation_service.get_recent(limit)


@router.get("/page", response_model=PageResponse[TaskEvaluationSummary])
def get_evaluation_page(
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    evaluation_service: Annotated[
        TaskEvaluationService,
        Depends(get_task_evaluation_service),
    ],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 5,
) -> PageResponse[TaskEvaluationSummary]:
    """Trả Evaluation và metadata phân trang trong một response."""

    return evaluation_service.get_page(page=page, page_size=page_size)


@router.get("/tasks/{task_id}", response_model=TaskEvaluationDetail | None)
def get_task_evaluation(
    task_id: str,
    execution_service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    evaluation_service: Annotated[
        TaskEvaluationService,
        Depends(get_task_evaluation_service),
    ],
) -> TaskEvaluationDetail | None:
    """Task must exist. Null means no persisted evaluation, not a FAIL result."""

    execution_service.get_task(task_id)
    return evaluation_service.get_by_task_id(task_id)
