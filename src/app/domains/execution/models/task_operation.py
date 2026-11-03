"""SQLAlchemy model ánh xạ bảng task_operations."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import OperationStatus


class OperationModel(Base):
    __tablename__ = "task_operations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    operation_intent: Mapped[str] = mapped_column(String(100))
    display_order: Mapped[int] = mapped_column(Integer)
    operation_status: Mapped[OperationStatus] = mapped_column(Enum(OperationStatus, name="operation_status"))
    operation_parameters: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
