"""HTTP routes quản lý vai trò."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.domains.identity.routers.dependencies import (
    get_role_service,
    require_permission,
)
from app.domains.identity.schemas import Role, RoleCreate, RoleUpdate, User
from app.domains.identity.services import RoleService


router = APIRouter()


# CREATE — Thêm vai trò mới.
@router.post(
    "/",
    response_model=Role,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm vai trò",
)
async def create_role(
    payload: RoleCreate,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[
        User,
        Depends(require_permission("Role-Based Access", "Add")),
    ],
) -> Role:
    """Tạo role và ghi nhận user thực hiện vào dữ liệu audit."""

    return service.create_role(payload, current_user.id)


# UPDATE — Sửa vai trò theo ID.
@router.patch(
    "/{role_id}",
    response_model=Role,
    summary="Cập nhật vai trò",
)
async def update_role(
    role_id: str,
    payload: RoleUpdate,
    service: Annotated[RoleService, Depends(get_role_service)],
    current_user: Annotated[
        User,
        Depends(require_permission("Role-Based Access", "Edit")),
    ],
) -> Role:
    """Cập nhật role và ghi nhận user sửa gần nhất."""

    return service.update_role(role_id, payload, current_user.id)


# READ và DELETE chưa được triển khai trong phạm vi hiện tại.
