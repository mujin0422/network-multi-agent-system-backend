"""Request, response và record schema của benchmark_scenarios."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.benchmark.schemas.common import (
    BenchmarkAction,
    BenchmarkCheck,
    BenchmarkRootCause,
)


class BenchmarkScenario(BaseModel):
    """Thông tin cơ bản của một benchmark scenario."""
    model_config = ConfigDict(str_strip_whitespace=True)

    scenario_key: str = Field(max_length=100, pattern=r"^[a-z0-9][a-z0-9-]*$", description="Khóa duy nhất của benchmark scenario, dùng để tham chiếu.")
    version: str = Field(min_length=1, max_length=30, description="Phiên bản của benchmark scenario.")
    name: str = Field(min_length=1, max_length=100, description="Tên của benchmark scenario.")
    description: str = Field(min_length=1, max_length=500, description="Mô tả của benchmark scenario.")
    topology: str = Field(min_length=1, max_length=100, description="Tên topology của benchmark scenario.")
    initial_message: str = Field(min_length=1, description="Nội dung message khởi tạo benchmark scenario.")
    preconditions: list[BenchmarkCheck] = Field(default_factory=list, description="Danh sách các kiểm tra điều kiện tiên quyết của benchmark scenario.")
    injection: list[BenchmarkAction] = Field(min_length=1, description="Danh sách các hành động được inject vào benchmark scenario.")
    fault_verification: list[BenchmarkCheck] = Field(min_length=1, description="Danh sách các kiểm tra để xác minh lỗi.")
    ground_truth: list[BenchmarkRootCause] = Field(min_length=1, description="Danh sách các nguyên nhân gốc.")
    evaluation_required_terms: list[str] = Field(min_length=1, description="Danh sách các điều kiện đánh giá cần thiết.")
    cleanup: list[BenchmarkAction] = Field(min_length=1, description="Danh sách các hành động dọn dẹp.")


class BenchmarkScenarioSummary(BaseModel):
    """Thông tin tóm tắt của một benchmark scenario, dùng trong danh sách scenario."""
    id: str = Field(pattern=r"^benc-\d{6}-[0-9a-f]{8}$", description="ID của benchmark scenario.")
    scenario_key: str = Field(description="Khóa duy nhất của benchmark scenario, dùng để tham chiếu.")
    version: str = Field(description="Phiên bản của benchmark scenario.")
    name: str = Field(description="Tên của benchmark scenario.")
    description: str = Field(description="Mô tả của benchmark scenario.")
    topology: str = Field(description="Tên topology của benchmark scenario.")
    initial_message: str = Field(description="Nội dung message khởi tạo benchmark scenario.")
    is_active: bool = Field(default=True, description="True nếu scenario đang hoạt động, False nếu không.")
    created_at: datetime | None = Field(default=None, description="Thời điểm tạo scenario.")
    last_updated_at: datetime | None = Field(default=None, description="Thời điểm cập nhật scenario gần nhất.")


class BenchmarkScenarioRecord(BenchmarkScenario):
    """Bản ghi chi tiết của một benchmark scenario, bao gồm các metadata quản lý."""
    id: str = Field(pattern=r"^benc-\d{6}-[0-9a-f]{8}$", description="ID của benchmark scenario.")
    is_active: bool = Field(default=True, description="True nếu scenario đang hoạt động, False nếu không.")
    created_by: str | None = Field(default=None, description="Người tạo scenario.")
    last_updated_by: str | None = Field(default=None, description="Người cập nhật scenario gần nhất.")
    created_at: datetime = Field(description="Thời điểm tạo scenario.")
    last_updated_at: datetime = Field(description="Thời điểm cập nhật scenario gần nhất.")

    @model_validator(mode="before")
    @classmethod
    def merge_definition(cls, value: object) -> object:
        """Trải definition JSONB của ORM thành các trường scenario."""

        if isinstance(value, dict) or not hasattr(value, "definition"):
            return value
        return {
            "id": value.id,
            "scenario_key": value.scenario_key,
            "version": value.version,
            "name": value.name,
            "description": value.description,
            "topology": value.topology,
            "initial_message": value.initial_message,
            **value.definition,
            "is_active": value.is_active,
            "created_by": value.created_by,
            "last_updated_by": value.last_updated_by,
            "created_at": value.created_at,
            "last_updated_at": value.last_updated_at,
        }


class BenchmarkScenarioUpdate(BaseModel):
    """Dữ liệu dùng để cập nhật một benchmark scenario."""
    version: str | None = Field(default=None, min_length=1, max_length=30, description="Phiên bản của scenario.")
    name: str | None = Field(default=None, min_length=1, max_length=100, description="Tên của scenario.")
    description: str | None = Field(default=None, min_length=1, max_length=500, description="Mô tả của scenario.")
    topology: str | None = Field(default=None, min_length=1, max_length=100, description="Topology của scenario.")
    initial_message: str | None = Field(default=None, min_length=1, description="Nội dung message khởi tạo benchmark scenario.")
    preconditions: list[BenchmarkCheck] | None = Field(default=None, description="Các điều kiện tiền đề của scenario.")
    injection: list[BenchmarkAction] | None = Field(default=None, min_length=1, description="Các hành động tiêm vào scenario.")
    fault_verification: list[BenchmarkCheck] | None = Field(default=None, min_length=1, description="Các kiểm tra lỗi của scenario.")
    ground_truth: list[BenchmarkRootCause] | None = Field(default=None, min_length=1, description="Các nguyên nhân gốc rễ của scenario.")
    evaluation_required_terms: list[str] | None = Field(default=None, min_length=1, description="Các điều kiện đánh giá cần thiết của scenario.")
    cleanup: list[BenchmarkAction] | None = Field(default=None, min_length=1, description="Các hành động dọn dẹp của scenario.")
    is_active: bool | None = Field(default=None, description="True nếu scenario đang hoạt động, False nếu không.")