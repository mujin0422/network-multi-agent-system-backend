"""SQLAlchemy model ánh xạ bảng operation_dependencies."""

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import DependencyType


class OperationDependencyModel(Base):
    __tablename__ = "operation_dependencies"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation_id: Mapped[str] = mapped_column(ForeignKey("task_operations.id"))
    depends_on_operation_id: Mapped[str] = mapped_column(
        ForeignKey("task_operations.id")
    )
    dependency_type: Mapped[DependencyType] = mapped_column(
        Enum(DependencyType, name="dependency_type")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
