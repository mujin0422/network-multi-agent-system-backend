"""Request, response và record schema của benchmark_runs."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.domains.benchmark.schemas.benchmark_scenario import BenchmarkScenario


class BenchmarkRunStatus(StrEnum):
    """Trạng thái của benchmark run."""
    PREPARING = "PREPARING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CLEANED = "CLEANED"


class BenchmarkRun(BaseModel):
    """Thông tin cơ bản của một benchmark run."""
    id: str = Field(pattern=r"^benr-\d{6}-[0-9a-f]{8}$", description="ID của benchmark run.")
    scenario_id: str = Field(pattern=r"^benc-\d{6}-[0-9a-f]{8}$", description="ID của scenario.")
    scenario_version: str = Field(description="Phiên bản của scenario.")
    scenario_name: str = Field(description="Tên của scenario.")
    status: BenchmarkRunStatus = Field(description="Trạng thái của benchmark run.")
    started_by: str = Field(description="Người bắt đầu benchmark run.")
    initial_message: str = Field(description="Nội dung message khởi tạo benchmark run.")
    conversation_id: str | None = Field(default=None, description="ID conversation của benchmark run.")
    source_message_id: str | None = Field(default=None, description="ID message nguồn của benchmark run.")
    task_id: str | None = Field(default=None, description="ID task của benchmark run.")
    evaluation_id: str | None = Field(default=None, description="ID evaluation của benchmark run.")
    evaluation_result: str | None = Field(default=None, description="Kết quả đánh giá của benchmark run.")
    cleanup_required: bool = Field(default=False, description="True nếu cần dọn dẹp benchmark run.")
    error_message: str | None = Field(default=None, description="Thông báo lỗi của benchmark run.")
    started_at: datetime = Field(description="Thời điểm bắt đầu benchmark run.")
    completed_at: datetime | None = Field(default=None, description="Thời điểm hoàn thành benchmark run.")
    cleaned_at: datetime | None = Field(default=None, description="Thời điểm dọn dẹp benchmark run.")

    @field_validator("evaluation_id", mode="before")
    @classmethod
    def normalize_evaluation_id(cls, value: object) -> object:
        """Chuẩn hóa UUID từ ORM thành chuỗi dùng trong API."""
        return str(value) if value is not None else None


class BenchmarkRunRecord(BenchmarkRun):
    """Bản ghi chi tiết của một benchmark run, bao gồm snapshot của scenario."""
    scenario_snapshot: BenchmarkScenario


class BenchmarkRunPage(BaseModel):
    """Một trang benchmark run cùng metadata phân trang."""

    items: list[BenchmarkRun] = Field(default_factory=list)
    page: int = Field(ge=1, description="Số trang hiện tại, bắt đầu từ 1.")
    page_size: int = Field(ge=1, description="Số lượng mục trên mỗi trang.")
    total: int = Field(ge=0, description="Tổng số mục.")
    total_pages: int = Field(ge=0, description="Tổng số trang.")


class BenchmarkStartRequest(BaseModel):
    """Yêu cầu bắt đầu một benchmark run."""
    scenario_id: str = Field(pattern=r"^benc-\d{6}-[0-9a-f]{8}$")
