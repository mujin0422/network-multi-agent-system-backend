"""SQLAlchemy model cho hàng đợi AI workflow."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.workflow_job.schemas import WorkflowJobStatus, WorkflowJobType


class WorkflowJobModel(Base):
    __tablename__ = "workflow_jobs"

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    job_type: Mapped[WorkflowJobType] = mapped_column(
        Enum(WorkflowJobType, name="workflow_job_type"), nullable=False
    )
    deduplication_key: Mapped[str] = mapped_column(String(160), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    job_status: Mapped[WorkflowJobStatus] = mapped_column(
        Enum(WorkflowJobStatus, name="workflow_job_status"), nullable=False
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(160))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
