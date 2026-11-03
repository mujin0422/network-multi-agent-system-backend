"""Aggregate Goal-based task success rate over all benchmark runs."""

from pydantic import BaseModel, Field


class BenchmarkRunSummary(BaseModel):
    total_runs: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    in_progress: int = Field(ge=0)
    not_started: int = Field(ge=0)
    setup_failed: int = Field(ge=0)
    unscored: int = Field(ge=0)
    eligible_runs: int = Field(ge=0)
    success_rate: float | None = Field(default=None, ge=0, le=100)
