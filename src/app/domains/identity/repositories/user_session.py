"""Repository cho User Session — quản lý phiên và rotate refresh token nguyên tử."""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select, update

from app.core.database import create_session_factory
from app.domains.identity.models import UserSessionModel
from app.domains.identity.schemas import UserSessionRecord

# =============================================================================
# User Session — quản lý phiên và rotate refresh token nguyên tử
# =============================================================================


class UserSessionRepositoryProtocol(Protocol):
    def save_session(self, session: UserSessionRecord) -> None: ...

    def get_session_by_hash(self, token_hash: str) -> UserSessionRecord | None: ...

    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None: ...

    def is_session_active(self, session_id: UUID) -> bool: ...

    def get_active_session(self, session_id: UUID) -> UserSessionRecord | None: ...

    def rotate_session(
        self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord
    ) -> bool: ...


class UserSessionRepository:
    """Sở hữu query và transaction cho User Session — quản lý phiên và rotate refresh token nguyên tử."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    @staticmethod
    def _session_record(model: UserSessionModel | None) -> UserSessionRecord | None:
        return (
            UserSessionRecord.model_validate(model, from_attributes=True)
            if model
            else None
        )

    def save_session(self, record: UserSessionRecord) -> None:
        with self._sessions.begin() as session:
            session.add(self._to_session_model(record))

    @staticmethod
    def _to_session_model(record: UserSessionRecord) -> UserSessionModel:
        return UserSessionModel(
            id=record.id,
            user_id=record.user_id,
            refresh_token_hash=record.refresh_token_hash,
            expires_at=record.expires_at,
            created_at=record.created_at,
            revoked_at=record.revoked_at,
        )

    def get_session_by_hash(self, token_hash: str) -> UserSessionRecord | None:
        with self._sessions() as session:
            model = session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.refresh_token_hash == token_hash
                )
            )
            return self._session_record(model)

    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None:
        statement = (
            update(UserSessionModel)
            .where(
                UserSessionModel.id == session_id, UserSessionModel.revoked_at.is_(None)
            )
            .values(revoked_at=revoked_at)
        )
        with self._sessions.begin() as session:
            session.execute(statement)

    def is_session_active(self, session_id: UUID) -> bool:
        return self.get_active_session(session_id) is not None

    def get_active_session(self, session_id: UUID) -> UserSessionRecord | None:
        statement = select(UserSessionModel).where(
            UserSessionModel.id == session_id,
            UserSessionModel.revoked_at.is_(None),
            UserSessionModel.expires_at > datetime.now(UTC),
        )
        with self._sessions() as session:
            return self._session_record(session.scalar(statement))

    def rotate_session(
        self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord
    ) -> bool:
        statement = (
            update(UserSessionModel)
            .where(
                UserSessionModel.id == session_id,
                UserSessionModel.revoked_at.is_(None),
                UserSessionModel.expires_at > revoked_at,
            )
            .values(revoked_at=revoked_at)
        )
        with self._sessions.begin() as session:
            result = session.execute(statement)
            if result.rowcount != 1:
                return False
            session.add(self._to_session_model(replacement))
        return True
