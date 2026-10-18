"""Persistence contract và PostgreSQL adapter cho resource Device."""

from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from app.domains.inventory.schemas import Device


class DeviceRepository(Protocol):
    """Cổng persistence tối thiểu mà ``DeviceService`` yêu cầu."""

    def save(self, device: Device) -> None: ...

    def get(self, device_id: str) -> Device | None: ...

    def get_by_hostname(self, hostname: str) -> Device | None: ...

    def list(self) -> list[Device]: ...


class PostgresDeviceRepository:
    """Lưu và đọc inventory từ bảng ``devices`` trong PostgreSQL.

    Repository chỉ truy vấn bảng thiết bị, không đọc hay trả về password/secret
    trong bảng ``credentials``.
    """

    _columns = """
        id, credential_id, brand_id, category_id, hostname, host, port,
        device_type, location, created_by, last_updated_by, created_at,
        last_updated_at
    """

    def __init__(self, database_url: str) -> None:
        # URL được lấy từ Settings/DI; repository không tự đọc environment.
        self._database_url = database_url

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def save(self, device: Device) -> None:
        """Insert hoặc update một device trong cùng một câu lệnh.

        ``ON CONFLICT (id)`` giúp cùng method phục vụ cả create và update.
        ``created_at`` không bị ghi đè khi update để bảo toàn thời điểm tạo.
        Context manager tự commit khi thành công và rollback khi có exception.
        """
        query = """
            INSERT INTO devices (
                id, credential_id, brand_id, category_id, hostname, host, port,
                device_type, location, created_by, last_updated_by, created_at,
                last_updated_at
            ) VALUES (
                %(id)s, %(credential_id)s, %(brand_id)s, %(category_id)s,
                %(hostname)s, %(host)s, %(port)s, %(device_type)s,
                %(location)s, %(created_by)s, %(last_updated_by)s, %(created_at)s,
                %(last_updated_at)s
            )
            ON CONFLICT (id) DO UPDATE SET
                credential_id = EXCLUDED.credential_id,
                brand_id = EXCLUDED.brand_id,
                category_id = EXCLUDED.category_id,
                hostname = EXCLUDED.hostname,
                host = EXCLUDED.host,
                port = EXCLUDED.port,
                device_type = EXCLUDED.device_type,
                location = EXCLUDED.location,
                last_updated_by = EXCLUDED.last_updated_by,
                last_updated_at = EXCLUDED.last_updated_at
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, device.model_dump())

    def get(self, device_id: str) -> Device | None:
        """Đọc một thiết bị bằng primary key và validate thành schema Device."""
        query = f"SELECT {self._columns} FROM devices WHERE id = %s"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (device_id,))
                row = cursor.fetchone()
        return Device.model_validate(row) if row else None

    def get_by_hostname(self, hostname: str) -> Device | None:
        """Đọc một thiết bị theo hostname, không phân biệt hoa thường."""

        query = f"""
            SELECT {self._columns}
            FROM devices
            WHERE lower(hostname) = lower(%s)
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (hostname,))
                row = cursor.fetchone()
        return Device.model_validate(row) if row else None

    def list(self) -> list[Device]:
        """Đọc toàn bộ inventory theo thứ tự ổn định cho frontend."""
        # Sắp theo port rồi hostname để frontend luôn nhận thứ tự ổn định.
        query = f"SELECT {self._columns} FROM devices ORDER BY port, hostname"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        return [Device.model_validate(row) for row in rows]
