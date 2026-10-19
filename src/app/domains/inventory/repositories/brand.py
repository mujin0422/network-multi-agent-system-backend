"""Persistence port và adapters cho resource Brand."""

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.inventory.models import BrandModel
from app.domains.inventory.schemas import Brand


class BrandRepository(Protocol):
    """Persistence contract cho các use case Brand."""

    def save(self, brand: Brand) -> None: ...

    def get(self, brand_id: str) -> Brand | None: ...

    def list(self) -> list[Brand]: ...


class PostgresBrandRepository:
    """Đọc brand và supported driver từ bảng ``brands``."""

    def __init__(self, database_url: str) -> None:
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

    def get(self, brand_id: str) -> Brand | None:
        """Lấy một Brand theo primary key."""

        with self._sessions() as session:
            model = session.get(BrandModel, brand_id)
            return Brand.model_validate(model, from_attributes=True) if model else None

    def list(self) -> list[Brand]:
        """Trả toàn bộ brand theo thứ tự tên ổn định cho frontend."""

        statement = select(BrandModel).order_by(BrandModel.name, BrandModel.id)
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [Brand.model_validate(item, from_attributes=True) for item in models]
