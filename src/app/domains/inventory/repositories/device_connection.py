"""Persistence adapters used to build connection-ready device configuration."""

from typing import Protocol

from app.domains.inventory.schemas import DeviceConfig


class DeviceConfigRepository(Protocol):
    """Contract for retrieving one device together with its credential."""

    def get(self, device_identifier: str) -> DeviceConfig | None: ...


class PostgresDeviceConfigRepository:
    """Read device metadata and decrypted credentials from PostgreSQL.

    Password and enable secret are only materialized for the Netmiko connection
    flow. They are never returned by the public Inventory API.
    """

    def __init__(self, database_url: str, encryption_key: str) -> None:
        self._database_url = database_url
        self._encryption_key = encryption_key

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self._database_url, row_factory=dict_row)

    def get(self, device_identifier: str) -> DeviceConfig | None:
        # Cho phép agent gọi bằng cả primary key (devc-...) và hostname (P1).
        # Credential chỉ được giải mã trong luồng kết nối và không được ghi log.
        query = """
            SELECT
                d.device_type,
                d.host AS hostname,
                d.port,
                c.username,
                pgp_sym_decrypt(dearmor(c.password), %s) AS password,
                CASE
                    WHEN c.secret IS NULL THEN ''
                    ELSE pgp_sym_decrypt(dearmor(c.secret), %s)
                END AS secret
            FROM devices AS d
            JOIN credentials AS c ON c.id = d.credential_id
            WHERE d.id = %s OR lower(d.hostname) = lower(%s)
            ORDER BY CASE WHEN d.id = %s THEN 0 ELSE 1 END
            LIMIT 1
        """
        params = (
            self._encryption_key,
            self._encryption_key,
            device_identifier,
            device_identifier,
            device_identifier,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                row = cursor.fetchone()
        return DeviceConfig.model_validate(row) if row else None
