"""HTTP API quản lý benchmark_scenarios."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.domains.benchmark.routers.dependencies import get_benchmark_scenario_service
from app.domains.benchmark.schemas import (
    BenchmarkScenario,
    BenchmarkScenarioRecord,
    BenchmarkScenarioSummary,
    BenchmarkScenarioUpdate,
)
from app.domains.benchmark.services import BenchmarkScenarioService
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User


router = APIRouter(prefix="/scenarios")


@router.get("", response_model=list[BenchmarkScenarioSummary])
async def list_scenarios(
    service: Annotated[
        BenchmarkScenarioService, Depends(get_benchmark_scenario_service)
    ],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> list[BenchmarkScenarioSummary]:
    return service.list()


@router.post("", response_model=BenchmarkScenarioSummary)
async def create_scenario(
    payload: BenchmarkScenario,
    service: Annotated[
        BenchmarkScenarioService, Depends(get_benchmark_scenario_service)
    ],
    user: Annotated[User, Depends(require_permission("Task Management", "Add"))],
) -> BenchmarkScenarioRecord:
    return service.create(payload, user.id)


@router.patch("/{scenario_id}", response_model=BenchmarkScenarioSummary)
async def update_scenario(
    scenario_id: str,
    payload: BenchmarkScenarioUpdate,
    service: Annotated[
        BenchmarkScenarioService, Depends(get_benchmark_scenario_service)
    ],
    user: Annotated[User, Depends(require_permission("Task Management", "Edit"))],
) -> BenchmarkScenarioRecord:
    return service.update(scenario_id, payload, user.id)
