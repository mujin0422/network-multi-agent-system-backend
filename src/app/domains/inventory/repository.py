"""Persistence contract và các adapter của Inventory domain."""

from typing import Protocol

from app.domains.inventory.schemas import Device


class DeviceRepository(Protocol):
    def save(self, device: Device) -> None: ...

    def get(self, device_id: str) -> Device | None: ...

    def list(self) -> list[Device]: ...


class InMemoryDeviceRepository:
    """Kho dữ liệu thử nghiệm; có thể thay bằng SQL repository qua DI."""

    def __init__(self) -> None:
        self._devices: dict[str, Device] = {}

    def save(self, device: Device) -> None:
        self._devices[device.id] = device.model_copy(deep=True)

    def get(self, device_id: str) -> Device | None:
        device = self._devices.get(device_id)
        return device.model_copy(deep=True) if device else None

    def list(self) -> list[Device]:
        return [item.model_copy(deep=True) for item in self._devices.values()]


class PostgresDeviceRepository:
    """Lưu và đọc inventory từ bảng ``devices`` trong PostgreSQL.

    Repository chỉ truy vấn bảng thiết bị, không đọc hay trả về password/secret
    trong bảng ``credentials``.
    """

    _columns = """
        id, credential_id, brand_id, category_id, hostname, host, port,
        device_type, location, last_updated_by, created_at, last_updated_at
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):
        # Import tại đây để unit test dùng in-memory adapter không bắt buộc phải
        # khởi động PostgreSQL. Docker image vẫn cài psycopg từ requirements.txt.
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self._database_url, row_factory=dict_row)

    def save(self, device: Device) -> None:
        query = """
            INSERT INTO devices (
                id, credential_id, brand_id, category_id, hostname, host, port,
                device_type, location, last_updated_by, created_at,
                last_updated_at
            ) VALUES (
                %(id)s, %(credential_id)s, %(brand_id)s, %(category_id)s,
                %(hostname)s, %(host)s, %(port)s, %(device_type)s,
                %(location)s, %(last_updated_by)s, %(created_at)s,
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
        query = f"SELECT {self._columns} FROM devices WHERE id = %s"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (device_id,))
                row = cursor.fetchone()
        return Device.model_validate(row) if row else None

    def list(self) -> list[Device]:
        # Sắp theo port rồi hostname để frontend luôn nhận thứ tự ổn định.
        query = f"SELECT {self._columns} FROM devices ORDER BY port, hostname"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        return [Device.model_validate(row) for row in rows]
