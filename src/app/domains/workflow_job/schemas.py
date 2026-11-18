"""Contracts của hàng đợi AI workflow."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowJobType(StrEnum):
    MESSAGE = "MESSAGE"
    APPROVAL = "APPROVAL"


class WorkflowJobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class WorkflowJob(BaseModel):
    id: UUID
    job_type: WorkflowJobType
    deduplication_key: str
    payload: dict[str, Any] = Field(default_factory=dict)
    job_status: WorkflowJobStatus
    attempts: int
    max_attempts: int
    available_at: datetime
    locked_at: datetime | None = None
    locked_by: str | None = None
    last_error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
