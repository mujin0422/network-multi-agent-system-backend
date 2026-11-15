"""Task-local activity observations for numerical benchmark evaluation."""

from datetime import datetime

from pydantic import BaseModel, Field


class ApprovalWaitInterval(BaseModel):
    """Khoảng thời gian chờ phê duyệt của một operation."""
    started_at: datetime = Field(description="Thời điểm bắt đầu chờ phê duyệt.")
    resumed_at: datetime = Field(description="Thời điểm tiếp tục thực thi sau khi phê duyệt.")


class BenchmarkObservation(BaseModel):
    """Các quan sát của Task được ghi nhận trong quá trình thực thi, phục vụ đánh giá benchmark."""
    source_message_created_at: datetime | None = Field(default=None, description="Thời điểm tạo message nguồn của Task.")
    agent_tool_calls: int | None = Field(default=None, ge=0, description="Số lần agent gọi tool trong quá trình thực thi Task.")
    approval_wait_intervals: list[ApprovalWaitInterval] = Field(default_factory=list, description="Danh sách các khoảng thời gian chờ phê duyệt của các operation.")
    approval_wait_open: bool = Field(default=False, description="True nếu đang chờ phê duyệt operation; False nếu không.")
    diagnosis_submission: dict | None = Field(default=None, description="Bản ghi nhận chẩn đoán của agent.")
    evidence_coverage: dict | None = Field(default=None, description="Mức độ bao phủ bằng chứng.")
