"""Request, response và record schema của benchmark_runs."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.domains.benchmark.schemas.benchmark_scenario import BenchmarkScenario


class BenchmarkRunStatus(StrEnum):
    PREPARING = "PREPARING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CLEANED = "CLEANED"


class BenchmarkRun(BaseModel):
    id: str = Field(pattern=r"^benr-\d{6}-[0-9a-f]{8}$")
    scenario_id: str = Field(pattern=r"^benc-\d{6}-[0-9a-f]{8}$")
    scenario_version: str
    scenario_name: str
    status: BenchmarkRunStatus
    started_by: str
    initial_message: str
    conversation_id: str | None = None
    source_message_id: str | None = None
    task_id: str | None = None
    evaluation_id: str | None = None
    evaluation_result: str | None = None
    cleanup_required: bool = False
    error_message: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    cleaned_at: datetime | None = None

    @field_validator("evaluation_id", mode="before")
    @classmethod
    def normalize_evaluation_id(cls, value: object) -> object:
        """Chuẩn hóa UUID từ ORM thành chuỗi dùng trong API."""

        return str(value) if value is not None else None


class BenchmarkRunRecord(BenchmarkRun):
    scenario_snapshot: BenchmarkScenario


class BenchmarkRunPage(BaseModel):
    """Một trang benchmark run cùng metadata phân trang."""

    items: list[BenchmarkRun]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    total_pages: int = Field(ge=0)


class BenchmarkStartRequest(BaseModel):
    scenario_id: str = Field(pattern=r"^benc-\d{6}-[0-9a-f]{8}$")
