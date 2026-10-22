"""Schema ánh xạ bảng ``operation_device_approvals``."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class OperationDeviceApprovalDecision(BaseModel):
    """Quyết định cuối cùng do User gửi cho một Approval đang PENDING."""

    decision: ApprovalDecision = Field(
        description="Chỉ chấp nhận APPROVED hoặc REJECTED.",
    )


class OperationDeviceApproval(BaseModel):
    """Quyết định phê duyệt duy nhất cho một operation-device WRITE."""

    id: str = Field(description="Khóa chính của approval.")
    operation_device_id: str = Field(description="ID mapping operation-device WRITE.")
    approval_status: ApprovalStatus = Field(description="Trạng thái phê duyệt.")
    risk_level: RiskLevel = Field(description="Mức rủi ro của thay đổi.")
    requested_by: str = Field(
        min_length=1,
        max_length=100,
        description="Agent hoặc thành phần tạo yêu cầu.",
    )
    reason: str = Field(min_length=1, description="Lý do cần phê duyệt.")
    commands_snapshot: list[str] = Field(
        min_length=1,
        description="Command WRITE bất biến đã trình cho người dùng.",
    )
    request_hash: str = Field(
        min_length=1,
        max_length=128,
        description="Hash của mapping và command snapshot.",
    )
    decided_by: str | None = Field(default=None, description="ID User ra quyết định.")
    requested_at: datetime = Field(description="Thời điểm yêu cầu phê duyệt.")
    decided_at: datetime | None = Field(default=None, description="Thời điểm quyết định.")
    expires_at: datetime | None = Field(default=None, description="Thời điểm hết hạn.")
    created_at: datetime = Field(description="Thời điểm tạo bản ghi.")


class OperationDeviceApprovalResponse(BaseModel):
    """Approval an toàn để trả qua API, không công khai request_hash."""

    id: str = Field(description="Khóa chính của approval.")
    operation_device_id: str = Field(description="ID mapping operation-device WRITE.")
    approval_status: ApprovalStatus = Field(description="Trạng thái phê duyệt.")
    risk_level: RiskLevel = Field(description="Mức rủi ro của thay đổi.")
    requested_by: str = Field(description="Agent hoặc thành phần tạo yêu cầu.")
    reason: str = Field(description="Lý do cần phê duyệt.")
    commands_snapshot: list[str] = Field(description="Command WRITE đã trình bày.")
    decided_by: str | None = Field(default=None, description="ID User ra quyết định.")
    requested_at: datetime = Field(description="Thời điểm yêu cầu phê duyệt.")
    decided_at: datetime | None = Field(default=None, description="Thời điểm quyết định.")
    expires_at: datetime | None = Field(default=None, description="Thời điểm hết hạn.")
    created_at: datetime = Field(description="Thời điểm tạo bản ghi.")
