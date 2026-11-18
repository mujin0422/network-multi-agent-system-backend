"""Composition root cho workflow queue."""

from functools import lru_cache

from app.core.config import get_settings
from app.domains.workflow_job.repository import WorkflowJobRepository
from app.domains.workflow_job.service import WorkflowJobService


@lru_cache
def build_workflow_job_service() -> WorkflowJobService:
    settings = get_settings()
    return WorkflowJobService(
        WorkflowJobRepository(settings.database_url),
        max_attempts=settings.workflow_job_max_attempts,
        retry_delay_seconds=settings.workflow_job_retry_delay_seconds,
        lock_timeout_seconds=settings.workflow_job_lock_timeout_seconds,
    )


async def get_workflow_job_service() -> WorkflowJobService:
    return build_workflow_job_service()
