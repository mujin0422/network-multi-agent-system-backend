"""Persistence port và adapters cho resource Brand."""

from __future__ import annotations

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.inventory.models import BrandModel
from app.domains.inventory.schemas import Brand


class BrandRepositoryProtocol(Protocol):
    """Persistence contract cho các use case Brand."""

    def save(self, brand: Brand) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save."""
        ...

    def get_by_id(self, brand_id: str) -> Brand | None:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        ...

    def get_all(self) -> list[Brand]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all."""
        ...


class BrandRepository:
    """Đọc brand và supported driver từ bảng ``brands``."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo BrandRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    def save(self, brand: Brand) -> None:
        """Thêm mới hoặc cập nhật Brand theo primary key."""

        with self._sessions.begin() as session:
            model = session.get(BrandModel, brand.id)
            if model is None:
                session.add(BrandModel(**brand.model_dump()))
                return
            model.name = brand.name
            model.supported_drivers = brand.supported_drivers

    def get_by_id(self, brand_id: str) -> Brand | None:
        """Lấy một Brand theo primary key."""

        with self._sessions() as session:
            model = session.get(BrandModel, brand_id)
            return Brand.model_validate(model, from_attributes=True) if model else None

    def get_all(self) -> list[Brand]:
        """Trả toàn bộ Brand từ database."""

        statement = select(BrandModel)
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [Brand.model_validate(item, from_attributes=True) for item in models]
