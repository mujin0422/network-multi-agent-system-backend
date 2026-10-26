"""ORM mapping cho bảng permissions."""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# =============================================================================
# permissions
# =============================================================================


class PermissionModel(Base):
    __tablename__ = "permissions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    function_id: Mapped[str] = mapped_column(ForeignKey("management_functions.id"))
    action_id: Mapped[str] = mapped_column(ForeignKey("actions.id"))
