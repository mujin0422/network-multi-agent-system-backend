"""Persistence port và PostgreSQL adapter cho resource Credential."""

from typing import Protocol

from sqlalchemy import func, select, update

from app.core.database import create_session_factory
from app.domains.inventory.models import CredentialModel
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

    def __init__(self, database_url: str, encryption_key: str) -> None:
        self._sessions = create_session_factory(database_url)
        self._encryption_key = encryption_key

    def _encrypted(self, value: str):
        return func.armor(
            func.pgp_sym_encrypt(
                value,
                self._encryption_key,
                "cipher-algo=aes256,compress-algo=1",
            )
        )

    def create(self, credential: Credential, password: str, secret: str | None) -> None:
        """Mã hóa password/secret bằng AES-256 trước khi insert."""

        model = CredentialModel(
            **credential.model_dump(),
            password=self._encrypted(password),
            secret=self._encrypted(secret) if secret is not None else None,
        )
        with self._sessions.begin() as session:
            session.add(model)

    def update(
        self,
        credential: Credential,
        password: str | None,
        secret: str | None,
        update_password: bool,
        update_secret: bool,
    ) -> None:
        """Cập nhật metadata và chỉ mã hóa lại secret được gửi trong request."""

        values = credential.model_dump(exclude={"id", "created_by", "created_at"})
        if update_password and password is not None:
            values["password"] = self._encrypted(password)
        if update_secret:
            values["secret"] = self._encrypted(secret) if secret is not None else None
        statement = (
            update(CredentialModel)
            .where(CredentialModel.id == credential.id)
            .values(**values)
        )
        with self._sessions.begin() as session:
            session.execute(statement)

    def get(self, credential_id: str) -> Credential | None:
        """Lấy metadata Credential theo ID, không đọc ciphertext."""

        with self._sessions() as session:
            model = session.get(CredentialModel, credential_id)
            return Credential.model_validate(model, from_attributes=True) if model else None

    def list(self) -> list[Credential]:
        """Lấy toàn bộ metadata Credential từ database."""

        statement = select(CredentialModel)
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [
                Credential.model_validate(item, from_attributes=True) for item in models
            ]
