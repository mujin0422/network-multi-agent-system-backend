"""Persistence port và PostgreSQL adapter cho resource Category."""

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.inventory.models import CategoryModel
from app.domains.inventory.schemas import Category


class CategoryRepository(Protocol):
    """Persistence contract cho use case lấy danh sách Category."""

    def list(self) -> list[Category]: ...


class PostgresCategoryRepository:
    """Đọc loại thiết bị từ bảng ``categories``."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def list(self) -> list[Category]:
        """Trả toàn bộ Category theo thứ tự tên ổn định cho frontend."""

        statement = select(CategoryModel).order_by(CategoryModel.name, CategoryModel.id)
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [Category.model_validate(item, from_attributes=True) for item in models]
