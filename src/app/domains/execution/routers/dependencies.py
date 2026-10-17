"""Dependency composition for Execution HTTP routes."""

from functools import lru_cache

from app.domains.execution import ExecutionService, InMemoryExecutionRepository


@lru_cache
def _build_execution_service() -> ExecutionService:
    return ExecutionService(InMemoryExecutionRepository())


async def get_execution_service() -> ExecutionService:
    return _build_execution_service()
