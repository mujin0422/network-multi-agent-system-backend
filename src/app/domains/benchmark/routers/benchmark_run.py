"""HTTP API điều khiển và tra cứu benchmark_runs."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.domains.benchmark.routers.dependencies import get_benchmark_run_service
from app.domains.benchmark.schemas import BenchmarkRun, BenchmarkRunPage, BenchmarkStartRequest
from app.domains.benchmark.schemas.benchmark_run_summary import BenchmarkRunSummary
from app.domains.benchmark.services import BenchmarkRunService
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User


router = APIRouter(prefix="/runs")


@router.post("", response_model=BenchmarkRun)
async def start_run(
    payload: BenchmarkStartRequest,
    service: Annotated[BenchmarkRunService, Depends(get_benchmark_run_service)],
    user: Annotated[User, Depends(require_permission("Task Management", "Add"))],
) -> BenchmarkRun:
    return service.start(payload.scenario_id, user.id)


@router.get("", response_model=list[BenchmarkRun])
async def list_runs(
    service: Annotated[BenchmarkRunService, Depends(get_benchmark_run_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    limit: int = 50,
) -> list[BenchmarkRun]:
    return service.list_runs(min(max(limit, 1), 100))


@router.get("/summary", response_model=BenchmarkRunSummary)
async def get_run_summary(
    service: Annotated[BenchmarkRunService, Depends(get_benchmark_run_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> BenchmarkRunSummary:
    """TSR across full run history (not limited by the list pagination)."""
    return service.get_summary()


@router.get("/page", response_model=BenchmarkRunPage)
async def get_run_page(
    service: Annotated[BenchmarkRunService, Depends(get_benchmark_run_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> BenchmarkRunPage:
    """Trả một trang benchmark run cùng tổng số bản ghi."""

    return service.get_run_page(page=page, page_size=page_size)


@router.get("/{run_id}", response_model=BenchmarkRun)
async def get_run(
    run_id: str,
    service: Annotated[BenchmarkRunService, Depends(get_benchmark_run_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> BenchmarkRun:
    return service.get_run(run_id)


@router.post("/{run_id}/cleanup", response_model=BenchmarkRun)
async def cleanup_run(
    run_id: str,
    service: Annotated[BenchmarkRunService, Depends(get_benchmark_run_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "Edit"))],
) -> BenchmarkRun:
    return service.cleanup(run_id)
