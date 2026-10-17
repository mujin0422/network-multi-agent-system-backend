"""Persistence port và adapters cho resource Brand."""

from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from app.domains.inventory.schemas import Brand


class BrandRepository(Protocol):
    """Persistence contract cho các use case Brand."""

    def save(self, brand: Brand) -> None: ...

    def get(self, brand_id: str) -> Brand | None: ...

    def list(self) -> list[Brand]: ...


class PostgresBrandRepository:
    """Đọc brand và supported driver từ bảng ``brands``."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def save(self, brand: Brand) -> None:
        """Thêm mới hoặc cập nhật Brand theo primary key."""

        query = """
            INSERT INTO brands (id, name, supported_drivers)
            VALUES (%(id)s, %(name)s, %(supported_drivers)s::jsonb)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                supported_drivers = EXCLUDED.supported_drivers
        """
        params = brand.model_dump()
        params["supported_drivers"] = psycopg.types.json.Jsonb(
            params["supported_drivers"]
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

    def get(self, brand_id: str) -> Brand | None:
        """Lấy một Brand theo primary key."""

        query = """
            SELECT id, name, supported_drivers
            FROM brands
            WHERE id = %s
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (brand_id,))
                row = cursor.fetchone()
        return Brand.model_validate(row) if row else None

    def list(self) -> list[Brand]:
        """Trả toàn bộ brand theo thứ tự tên ổn định cho frontend."""

        query = """
            SELECT id, name, supported_drivers
            FROM brands
            ORDER BY lower(name), id
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        return [Brand.model_validate(row) for row in rows]
