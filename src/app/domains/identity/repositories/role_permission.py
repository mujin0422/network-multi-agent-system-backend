"""Repository cho Role Permission — tra cứu quyền được gán cho role."""

from typing import Protocol

from sqlalchemy import delete, select

from app.core.database import create_session_factory
from app.domains.identity.models import (
    ActionModel,
    ManagementFunctionModel,
    PermissionModel,
    RolePermissionModel,
)
from app.domains.identity.schemas import (
    Action,
    ManagementFunction,
    Permission,
    RolePermission,
)

# =============================================================================
# Role Permission — tra cứu quyền được gán cho role
# =============================================================================


class RolePermissionRepositoryProtocol(Protocol):
    def get_by_role_id(self, role_id: str) -> set[tuple[str, str]]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_role_id."""
        ...

    def get_all_actions(self) -> list[Action]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_actions."""
        ...

    def get_all_management_functions(self) -> list[ManagementFunction]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_management_functions."""
        ...

    def get_all_permissions(self) -> list[Permission]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_permissions."""
        ...

    def get_all_by_role_id(self, role_id: str) -> list[RolePermission]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_by_role_id."""
        ...

    def replace_role_permissions(
        self, role_id: str, permission_ids: set[str]
    ) -> list[RolePermission]:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức replace_role_permissions."""
        ...


class RolePermissionRepository:
    """Sở hữu query và transaction cho Role Permission — tra cứu quyền được gán cho role."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo RolePermissionRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    def get_by_role_id(self, role_id: str) -> set[tuple[str, str]]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_role_id."""
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

    def get_all_actions(self) -> list[Action]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_actions."""
        with self._sessions() as session:
            rows = session.scalars(select(ActionModel).order_by(ActionModel.id)).all()
            return [Action.model_validate(row, from_attributes=True) for row in rows]

    def get_all_management_functions(self) -> list[ManagementFunction]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_management_functions."""
        with self._sessions() as session:
            rows = session.scalars(
                select(ManagementFunctionModel).order_by(ManagementFunctionModel.id)
            ).all()
            return [
                ManagementFunction.model_validate(row, from_attributes=True)
                for row in rows
            ]

    def get_all_permissions(self) -> list[Permission]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_permissions."""
        with self._sessions() as session:
            rows = session.scalars(
                select(PermissionModel).order_by(PermissionModel.id)
            ).all()
            return [Permission.model_validate(row, from_attributes=True) for row in rows]

    def get_all_by_role_id(self, role_id: str) -> list[RolePermission]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_by_role_id."""
        statement = (
            select(RolePermissionModel)
            .where(RolePermissionModel.role_id == role_id)
            .order_by(RolePermissionModel.permission_id)
        )
        with self._sessions() as session:
            rows = session.scalars(statement).all()
            return [
                RolePermission.model_validate(row, from_attributes=True)
                for row in rows
            ]

    def replace_role_permissions(
        self, role_id: str, permission_ids: set[str]
    ) -> list[RolePermission]:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức replace_role_permissions."""
        with self._sessions.begin() as session:
            session.execute(
                delete(RolePermissionModel).where(
                    RolePermissionModel.role_id == role_id
                )
            )
            session.add_all(
                RolePermissionModel(role_id=role_id, permission_id=permission_id)
                for permission_id in sorted(permission_ids)
            )
        return self.get_all_by_role_id(role_id)
