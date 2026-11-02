"""PostgreSQL repository cho resource Category."""

from __future__ import annotations

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.inventory.models import CategoryModel
from app.domains.inventory.schemas import Category


class CategoryRepository:
    """Đọc loại thiết bị từ bảng ``categories``."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def get_all(self) -> list[Category]:
        """Trả toàn bộ Category từ database."""

        statement = select(CategoryModel)
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [Category.model_validate(item, from_attributes=True) for item in models]
