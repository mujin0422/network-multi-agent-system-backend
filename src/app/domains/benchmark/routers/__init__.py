"""Public HTTP routers của Benchmark domain."""

from fastapi import APIRouter

from app.domains.benchmark.routers.benchmark_run import router as run_router
from app.domains.benchmark.routers.benchmark_scenario import router as scenario_router

router = APIRouter()
router.include_router(scenario_router)
router.include_router(run_router)

__all__ = ["router", "run_router", "scenario_router"]
