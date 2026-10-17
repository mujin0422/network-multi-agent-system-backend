"""Persistence port và PostgreSQL adapter cho resource Category."""

from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from app.domains.inventory.schemas import Category


class CategoryRepository(Protocol):
    """Persistence contract cho use case lấy danh sách Category."""

    def list(self) -> list[Category]: ...


class PostgresCategoryRepository:
    """Đọc loại thiết bị từ bảng ``categories``."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def list(self) -> list[Category]:
        """Trả toàn bộ Category theo thứ tự tên ổn định cho frontend."""

        query = """
            SELECT id, name
            FROM categories
            ORDER BY lower(name), id
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        return [Category.model_validate(row) for row in rows]
