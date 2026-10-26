"""Repository cho Role Permission — tra cứu quyền được gán cho role."""

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.identity.models import (
    ActionModel,
    ManagementFunctionModel,
    PermissionModel,
    RolePermissionModel,
)

# =============================================================================
# Role Permission — tra cứu quyền được gán cho role
# =============================================================================


class RolePermissionRepositoryProtocol(Protocol):
    def get_permissions(self, role_id: str) -> set[tuple[str, str]]: ...


class RolePermissionRepository:
    """Sở hữu query và transaction cho Role Permission — tra cứu quyền được gán cho role."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def get_permissions(self, role_id: str) -> set[tuple[str, str]]:
        statement = (
            select(ManagementFunctionModel.name, ActionModel.name)
            .join(
                PermissionModel,
                PermissionModel.function_id == ManagementFunctionModel.id,
            )
            .join(ActionModel, ActionModel.id == PermissionModel.action_id)
            .join(
                RolePermissionModel,
                RolePermissionModel.permission_id == PermissionModel.id,
            )
            .where(RolePermissionModel.role_id == role_id)
        )
        with self._sessions() as session:
            return {
                (function_name, action_name)
                for function_name, action_name in session.execute(statement)
            }
