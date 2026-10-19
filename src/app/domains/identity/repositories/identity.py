"""Identity persistence port and SQLAlchemy repository."""

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.database import create_session_factory
from app.domains.identity.models import ActionModel, ManagementFunctionModel, PermissionModel, RoleModel, RolePermissionModel, UserModel, UserSessionModel
from app.domains.identity.schemas import Role, User, UserRecord, UserSessionRecord


class IdentityRepository(Protocol):
    def get_user_by_email(self, email: str) -> UserRecord | None: ...
    def get_user(self, user_id: str) -> User | None: ...
    def list_users(self) -> list[User]: ...
    def get_user_with_password(self, user_id: str) -> UserRecord | None: ...
    def get_role(self, role_id: str) -> Role | None: ...
    def list_roles(self) -> list[Role]: ...
    def get_role_by_name(self, name: str) -> Role | None: ...
    def save_user(self, user: UserRecord) -> None: ...
    def save_role(self, role: Role) -> None: ...
    def get_permissions(self, role_id: str) -> set[tuple[str, str]]: ...
    def save_session(self, session: UserSessionRecord) -> None: ...
    def get_session_by_hash(self, token_hash: str) -> UserSessionRecord | None: ...
    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None: ...
    def is_session_active(self, session_id: UUID) -> bool: ...
    def get_active_session(self, session_id: UUID) -> UserSessionRecord | None: ...
    def rotate_session(self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord) -> bool: ...
    def update_login(self, user_id: str, logged_in_at: datetime) -> None: ...


class PostgresIdentityRepository:
    """Identity repository implemented with SQLAlchemy ORM."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    @staticmethod
    def _user_record(model: UserModel | None) -> UserRecord | None:
        return UserRecord.model_validate(model, from_attributes=True) if model else None

    @staticmethod
    def _session_record(model: UserSessionModel | None) -> UserSessionRecord | None:
        return UserSessionRecord.model_validate(model, from_attributes=True) if model else None

    def get_user_by_email(self, email: str) -> UserRecord | None:
        with self._sessions() as session:
            return self._user_record(session.scalar(select(UserModel).where(UserModel.email == email.lower())))

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

    def get_role(self, role_id: str) -> Role | None:
        with self._sessions() as session:
            model = session.get(RoleModel, role_id)
            return Role.model_validate(model, from_attributes=True) if model else None

    def list_roles(self) -> list[Role]:
        with self._sessions() as session:
            models = session.scalars(select(RoleModel)).all()
            return [
                Role.model_validate(model, from_attributes=True) for model in models
            ]

    def get_role_by_name(self, name: str) -> Role | None:
        statement = select(RoleModel).where(func.lower(RoleModel.name) == name.lower())
        with self._sessions() as session:
            model = session.scalar(statement)
            return Role.model_validate(model, from_attributes=True) if model else None

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

    def save_role(self, record: Role) -> None:
        with self._sessions.begin() as session:
            model = session.get(RoleModel, record.id)
            if model is None:
                session.add(RoleModel(**record.model_dump()))
                return
            model.name = record.name
            model.description = record.description
            model.last_updated_by = record.last_updated_by
            model.last_updated_at = record.last_updated_at

    def get_permissions(self, role_id: str) -> set[tuple[str, str]]:
        statement = select(ManagementFunctionModel.name, ActionModel.name).join(PermissionModel, PermissionModel.function_id == ManagementFunctionModel.id).join(ActionModel, ActionModel.id == PermissionModel.action_id).join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id).where(RolePermissionModel.role_id == role_id)
        with self._sessions() as session:
            return {(function_name, action_name) for function_name, action_name in session.execute(statement)}

    def save_session(self, record: UserSessionRecord) -> None:
        with self._sessions.begin() as session:
            session.add(self._to_session_model(record))

    @staticmethod
    def _to_session_model(record: UserSessionRecord) -> UserSessionModel:
        return UserSessionModel(id=record.id, user_id=record.user_id, refresh_token_hash=record.refresh_token_hash, expires_at=record.expires_at, created_at=record.created_at, revoked_at=record.revoked_at)

    def get_session_by_hash(self, token_hash: str) -> UserSessionRecord | None:
        with self._sessions() as session:
            model = session.scalar(select(UserSessionModel).where(UserSessionModel.refresh_token_hash == token_hash))
            return self._session_record(model)

    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None:
        statement = update(UserSessionModel).where(UserSessionModel.id == session_id, UserSessionModel.revoked_at.is_(None)).values(revoked_at=revoked_at)
        with self._sessions.begin() as session:
            session.execute(statement)

    def is_session_active(self, session_id: UUID) -> bool:
        return self.get_active_session(session_id) is not None

    def get_active_session(self, session_id: UUID) -> UserSessionRecord | None:
        statement = select(UserSessionModel).where(UserSessionModel.id == session_id, UserSessionModel.revoked_at.is_(None), UserSessionModel.expires_at > datetime.now(UTC))
        with self._sessions() as session:
            return self._session_record(session.scalar(statement))

    def rotate_session(self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord) -> bool:
        statement = update(UserSessionModel).where(UserSessionModel.id == session_id, UserSessionModel.revoked_at.is_(None), UserSessionModel.expires_at > revoked_at).values(revoked_at=revoked_at)
        with self._sessions.begin() as session:
            result = session.execute(statement)
            if result.rowcount != 1:
                return False
            session.add(self._to_session_model(replacement))
        return True

    def update_login(self, user_id: str, logged_in_at: datetime) -> None:
        statement = update(UserModel).where(UserModel.id == user_id).values(last_login_at=logged_in_at)
        with self._sessions.begin() as session:
            session.execute(statement)
