"""Schemas ánh xạ bảng ``permissions`` và ``role_permissions``."""

from pydantic import BaseModel, Field

from app.domains.identity.schemas.action import Action
from app.domains.identity.schemas.management_function import ManagementFunction


class Permission(BaseModel):
    """Một cặp function-action duy nhất."""

    id: str = Field(description="Khóa chính của permission.")
    function_id: str = Field(description="ID management function được bảo vệ.")
    action_id: str = Field(description="ID action được phép thực hiện.")


class RolePermission(BaseModel):
    """Quan hệ nhiều-nhiều giữa role và permission."""

    role_id: str = Field(description="ID role được cấp quyền.")
    permission_id: str = Field(description="ID permission được gán cho role.")


class PermissionCatalog(BaseModel):
    """Toàn bộ dữ liệu cần để dựng ma trận phân quyền."""

    functions: list[ManagementFunction]
    actions: list[Action]
    permissions: list[Permission]


class RolePermissionsUpdate(BaseModel):
    """Tập permission thay thế toàn bộ quyền hiện tại của một role."""

    permission_ids: list[str] = Field(default_factory=list)
