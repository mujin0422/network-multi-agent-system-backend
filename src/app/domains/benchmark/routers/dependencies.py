"""Dependency composition cho DB-backed GNS3 benchmark."""

from functools import lru_cache

from app.core.config import get_settings
from app.core.database import DatabaseUnitOfWork
from app.domains.benchmark.repositories import (
    BenchmarkRunRepository,
    BenchmarkScenarioRepository,
)
from app.domains.benchmark.services import BenchmarkRunService, BenchmarkScenarioService
from app.domains.evaluation.repositories import TaskEvaluationRepository
from app.domains.inventory.providers import DeviceConnectionProvider
from app.domains.inventory.repositories import DeviceConfigRepository
from app.domains.inventory.services import NetworkService
from app.tools import NetmikoNetworkTool


@lru_cache
def _build_benchmark_scenario_service() -> BenchmarkScenarioService:
    settings = get_settings()
    return BenchmarkScenarioService(
        BenchmarkScenarioRepository(settings.database_url),
        uow=DatabaseUnitOfWork.from_url(settings.database_url),
    )


@lru_cache
def _build_benchmark_run_service() -> BenchmarkRunService:
    settings = get_settings()
    credential_repository = DeviceConfigRepository(
        database_url=settings.database_url,
        encryption_key=settings.device_credential_encryption_key,
    )
    network_service = NetworkService(
        DeviceConnectionProvider(settings, credential_repository)
    )
    network_tool = NetmikoNetworkTool(
        network_service,
        settings.netmiko_read_timeout,
        settings.netmiko_cmd_verify,
    )
    return BenchmarkRunService(
        BenchmarkRunRepository(settings.database_url),
        BenchmarkScenarioRepository(settings.database_url),
        TaskEvaluationRepository(settings.database_url),
        network_tool,
        uow=DatabaseUnitOfWork.from_url(settings.database_url),
    )


async def get_benchmark_scenario_service() -> BenchmarkScenarioService:
    return _build_benchmark_scenario_service()


async def get_benchmark_run_service() -> BenchmarkRunService:
    return _build_benchmark_run_service()
