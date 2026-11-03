"""PostgreSQL repository cho resource Credential."""

from __future__ import annotations

from sqlalchemy import select, update

from app.core.database import create_session_factory
from app.domains.audit.transaction import append_audit_in_session
from app.domains.inventory.models import CredentialModel
from app.domains.inventory.schemas import Credential
from app.domains.inventory.utils import encrypted_credential


class CredentialRepository:
    """Lưu metadata và ciphertext Credential trong PostgreSQL."""

    def __init__(self, database_url: str, encryption_key: str) -> None:
        """Khởi tạo CredentialRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)
        self._encryption_key = encryption_key

    def create(
        self,
        credential: Credential,
        *,
        password: str,
        secret: str | None,
    ) -> None:
        """Mã hóa password/secret bằng AES-256 trước khi insert."""

        model = CredentialModel(
            **credential.model_dump(),
            password=encrypted_credential(password, self._encryption_key),
            secret=(
                encrypted_credential(secret, self._encryption_key)
                if secret is not None
                else None
            ),
        )
        with self._sessions.begin() as session:
            append_audit_in_session(session)
            session.add(model)

    def update(
        self,
        credential: Credential,
        *,
        password: str | None,
        secret: str | None,
        update_password: bool,
        update_secret: bool,
    ) -> None:
        """Cập nhật metadata và chỉ mã hóa lại secret được gửi trong request."""

        values = credential.model_dump(exclude={"id", "created_by", "created_at"})
        if update_password and password is not None:
            values["password"] = encrypted_credential(password, self._encryption_key)
        if update_secret:
            values["secret"] = (
                encrypted_credential(secret, self._encryption_key)
                if secret is not None
                else None
            )
        statement = (
            update(CredentialModel)
            .where(CredentialModel.id == credential.id)
            .values(**values)
        )
        with self._sessions.begin() as session:
            append_audit_in_session(session)
            session.execute(statement)

    def get_by_id(self, credential_id: str) -> Credential | None:
        """Lấy metadata Credential theo ID, không đọc ciphertext."""

        with self._sessions() as session:
            model = session.get(CredentialModel, credential_id)
            return Credential.model_validate(model, from_attributes=True) if model else None

    def get_all(self) -> list[Credential]:
        """Lấy toàn bộ metadata Credential từ database."""

        statement = select(CredentialModel)
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [
                Credential.model_validate(item, from_attributes=True) for item in models
            ]
