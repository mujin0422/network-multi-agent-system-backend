"""Dependency composition for Execution HTTP routes."""

from functools import lru_cache

from app.core.config import get_settings
from app.domains.execution.services import ExecutionService, build_execution_service


@lru_cache
def _build_execution_service() -> ExecutionService:
    return build_execution_service(get_settings().database_url)


async def get_execution_service() -> ExecutionService:
    return _build_execution_service()
