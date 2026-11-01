"""Persistence port và PostgreSQL adapter cho resource Category."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.inventory.models import CategoryModel
from app.domains.inventory.schemas import Category


class CategoryRepositoryProtocol(Protocol):
    """Persistence contract cho use case lấy danh sách Category."""

    def get_all(self) -> list[Category]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all."""
        ...


class CategoryRepository:
    """Đọc loại thiết bị từ bảng ``categories``."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo CategoryRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    def get_all(self) -> list[Category]:
        """Trả toàn bộ Category từ database."""

        statement = select(CategoryModel)
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [Category.model_validate(item, from_attributes=True) for item in models]
