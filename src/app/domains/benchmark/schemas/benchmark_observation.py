"""Raw observations collected for one benchmark task (not PASS/FAIL judgments)."""

from datetime import datetime

from pydantic import BaseModel, Field


class BenchmarkObservation(BaseModel):
    # The benchmark initial message is created after preconditions/fault injection.
    source_message_created_at: datetime | None = None
    # One persisted TaskExecution with non-null tool_name = one agent-tool turn.
    agent_tool_calls: int | None = Field(default=None, ge=0)
