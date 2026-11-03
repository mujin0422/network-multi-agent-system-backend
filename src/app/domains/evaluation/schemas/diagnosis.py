"""Neutral schema for machine-readable root-cause claims from any AI agent."""

from pydantic import BaseModel, Field


class PredictedRootCause(BaseModel):
    """A proposed fault source; benchmark ground truth is never loaded here."""

    device: str = Field(min_length=1, max_length=100)
    interface: str | None = Field(default=None, max_length=100)
    fault_type: str = Field(min_length=1, max_length=100)
