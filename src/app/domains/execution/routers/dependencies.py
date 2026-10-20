"""Dependency composition for Execution HTTP routes."""

from functools import lru_cache

from app.core.config import get_settings
from app.domains.execution import ExecutionRepository, ExecutionService


@lru_cache
def _build_execution_service() -> ExecutionService:
    repository = ExecutionRepository(get_settings().database_url)
    return ExecutionService(repository)


async def get_execution_service() -> ExecutionService:
    return _build_execution_service()
