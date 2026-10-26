"""ORM mapping cho bảng management_functions."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# =============================================================================
# management_functions
# =============================================================================


class ManagementFunctionModel(Base):
    __tablename__ = "management_functions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
