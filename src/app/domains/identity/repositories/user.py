"""Repository cho User — bảng users."""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select, update

from app.core.database import create_session_factory
from app.domains.identity.models import UserModel
from app.domains.identity.schemas import User, UserRecord

# =============================================================================
# User — bảng users
# =============================================================================


class UserRepositoryProtocol(Protocol):
    def get_user_by_email(self, email: str) -> UserRecord | None: ...

    def get_user(self, user_id: str) -> User | None: ...

    def list_users(self) -> list[User]: ...

    def get_user_with_password(self, user_id: str) -> UserRecord | None: ...

    def save_user(self, user: UserRecord) -> None: ...

    def update_login(self, user_id: str, logged_in_at: datetime) -> None: ...


class UserRepository:
    """Sở hữu query và transaction cho User — bảng users."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    @staticmethod
    def _user_record(model: UserModel | None) -> UserRecord | None:
        return UserRecord.model_validate(model, from_attributes=True) if model else None

    def get_user_by_email(self, email: str) -> UserRecord | None:
        with self._sessions() as session:
            return self._user_record(
                session.scalar(
                    select(UserModel).where(UserModel.email == email.lower())
                )
            )

    def get_user(self, user_id: str) -> User | None:
        with self._sessions() as session:
            model = session.get(UserModel, user_id)
            return User.model_validate(model, from_attributes=True) if model else None

    def list_users(self) -> list[User]:
        with self._sessions() as session:
            models = session.scalars(select(UserModel)).all()
            return [
                User.model_validate(model, from_attributes=True) for model in models
            ]

    def get_user_with_password(self, user_id: str) -> UserRecord | None:
        with self._sessions() as session:
            return self._user_record(session.get(UserModel, user_id))

    def save_user(self, record: UserRecord) -> None:
        with self._sessions.begin() as session:
            model = session.get(UserModel, record.id)
            if model is None:
                session.add(
                    UserModel(
                        id=record.id,
                        role_id=record.role_id,
                        email=record.email,
                        password_hash=record.password_hash,
                        full_name=record.full_name,
                        user_status=record.user_status,
                        created_at=record.created_at,
                        last_updated_at=record.last_updated_at,
                        last_login_at=record.last_login_at,
                    )
                )
                return
            model.role_id = record.role_id
            model.email = record.email
            model.password_hash = record.password_hash
            model.full_name = record.full_name
            model.user_status = record.user_status
            model.last_updated_at = record.last_updated_at
            model.last_login_at = record.last_login_at

    def update_login(self, user_id: str, logged_in_at: datetime) -> None:
        statement = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login_at=logged_in_at)
        )
        with self._sessions.begin() as session:
            session.execute(statement)
