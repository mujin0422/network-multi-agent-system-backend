"""Persistence port và PostgreSQL adapter cho resource Credential."""

from typing import Protocol

import psycopg
from psycopg.rows import dict_row

from app.domains.inventory.schemas import Credential


class CredentialRepository(Protocol):
    """Persistence contract cho các use case Credential."""

    def create(self, credential: Credential, password: str, secret: str | None) -> None: ...

    def update(
        self,
        credential: Credential,
        password: str | None,
        secret: str | None,
        update_password: bool,
        update_secret: bool,
    ) -> None: ...

    def get(self, credential_id: str) -> Credential | None: ...

    def list(self) -> list[Credential]: ...


class PostgresCredentialRepository:
    """Lưu metadata và ciphertext Credential trong PostgreSQL."""

    _columns = """
        id, name, description, username, encryption_type, created_by,
        last_updated_by, created_at, last_updated_at
    """

    def __init__(self, database_url: str, encryption_key: str) -> None:
        self._database_url = database_url
        self._encryption_key = encryption_key

    def _connect(self):
        return psycopg.connect(self._database_url, row_factory=dict_row)

    def create(self, credential: Credential, password: str, secret: str | None) -> None:
        """Mã hóa password/secret bằng AES-256 trước khi insert."""

        query = """
            INSERT INTO credentials (
                id, name, description, username, password, secret,
                encryption_type, created_by, last_updated_by,
                created_at, last_updated_at
            ) VALUES (
                %(id)s, %(name)s, %(description)s, %(username)s,
                armor(pgp_sym_encrypt(
                    %(password)s, %(encryption_key)s,
                    'cipher-algo=aes256,compress-algo=1'
                )),
                CASE WHEN %(secret)s IS NULL THEN NULL ELSE armor(pgp_sym_encrypt(
                    %(secret)s, %(encryption_key)s,
                    'cipher-algo=aes256,compress-algo=1'
                )) END,
                %(encryption_type)s, %(created_by)s, %(last_updated_by)s,
                %(created_at)s, %(last_updated_at)s
            )
        """
        params = credential.model_dump()
        params.update(
            password=password,
            secret=secret,
            encryption_key=self._encryption_key,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

    def update(
        self,
        credential: Credential,
        password: str | None,
        secret: str | None,
        update_password: bool,
        update_secret: bool,
    ) -> None:
        """Cập nhật metadata và chỉ mã hóa lại secret được gửi trong request."""

        query = """
            UPDATE credentials
            SET name = %(name)s,
                description = %(description)s,
                username = %(username)s,
                encryption_type = %(encryption_type)s,
                last_updated_by = %(last_updated_by)s,
                last_updated_at = %(last_updated_at)s,
                password = CASE WHEN %(update_password)s THEN armor(pgp_sym_encrypt(
                    %(password)s, %(encryption_key)s,
                    'cipher-algo=aes256,compress-algo=1'
                )) ELSE password END,
                secret = CASE
                    WHEN NOT %(update_secret)s THEN secret
                    WHEN %(secret)s IS NULL THEN NULL
                    ELSE armor(pgp_sym_encrypt(
                        %(secret)s, %(encryption_key)s,
                        'cipher-algo=aes256,compress-algo=1'
                    ))
                END
            WHERE id = %(id)s
        """
        params = credential.model_dump()
        params.update(
            password=password,
            secret=secret,
            update_password=update_password,
            update_secret=update_secret,
            encryption_key=self._encryption_key,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)

    def get(self, credential_id: str) -> Credential | None:
        """Lấy metadata Credential theo ID, không đọc ciphertext."""

        query = f"SELECT {self._columns} FROM credentials WHERE id = %s"
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (credential_id,))
                row = cursor.fetchone()
        return Credential.model_validate(row) if row else None

    def list(self) -> list[Credential]:
        """Lấy danh sách metadata Credential theo tên ổn định."""

        query = f"""
            SELECT {self._columns}
            FROM credentials
            ORDER BY lower(name), id
        """
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        return [Credential.model_validate(row) for row in rows]
