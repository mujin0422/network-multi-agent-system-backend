"""Task-local activity observations for numerical benchmark evaluation."""

from datetime import datetime

from pydantic import BaseModel, Field


class ApprovalWaitInterval(BaseModel):
    started_at: datetime
    resumed_at: datetime


class BenchmarkObservation(BaseModel):
    # Retained for inspection of old logs; no longer used to measure AI runtime.
    source_message_created_at: datetime | None = None
    agent_tool_calls: int | None = Field(default=None, ge=0)
    approval_wait_intervals: list[ApprovalWaitInterval] = Field(default_factory=list)
    approval_wait_open: bool = False
    # Agent's submission comes from ANALYSIS_COMPLETED, never from benchmark GT.
    diagnosis_submission: dict | None = None
