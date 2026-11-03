"""SQLAlchemy model ánh xạ bảng operation_device_approvals."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import ApprovalStatus, RiskLevel


class OperationDeviceApprovalModel(Base):
    __tablename__ = "operation_device_approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation_device_id: Mapped[str] = mapped_column(ForeignKey("task_operation_devices.id"), unique=True, nullable=False)
    approval_status: Mapped[ApprovalStatus] = mapped_column(Enum(ApprovalStatus, name="approval_status"), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel, name="risk_level"), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    commands_snapshot: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
