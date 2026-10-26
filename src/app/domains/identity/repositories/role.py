"""Repository cho Role — bảng roles."""

from typing import Protocol

from sqlalchemy import func, select

from app.core.database import create_session_factory
from app.domains.identity.models import RoleModel
from app.domains.identity.schemas import Role

# =============================================================================
# Role — bảng roles
# =============================================================================


class RoleRepositoryProtocol(Protocol):
    def get_role(self, role_id: str) -> Role | None: ...

    def list_roles(self) -> list[Role]: ...

    def get_role_by_name(self, name: str) -> Role | None: ...

    def save_role(self, role: Role) -> None: ...


class RoleRepository:
    """Sở hữu query và transaction cho Role — bảng roles."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

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
