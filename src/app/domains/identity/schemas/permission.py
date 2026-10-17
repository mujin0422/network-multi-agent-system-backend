"""Schemas ánh xạ bảng ``permissions`` và ``role_permissions``."""

from pydantic import BaseModel, Field


class Permission(BaseModel):
    """Một cặp function-action duy nhất."""

    id: str = Field(description="Khóa chính của permission.")
    function_id: str = Field(description="ID management function được bảo vệ.")
    action_id: str = Field(description="ID action được phép thực hiện.")


class RolePermission(BaseModel):
    """Quan hệ nhiều-nhiều giữa role và permission."""

    role_id: str = Field(description="ID role được cấp quyền.")
    permission_id: str = Field(description="ID permission được gán cho role.")
