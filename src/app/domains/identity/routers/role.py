"""HTTP routes quản lý vai trò."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.domains.identity.routers.dependencies import (
    get_access_control_service,
    get_role_service,
    require_permission,
)
from app.domains.identity.schemas import (
    PermissionCatalog,
    Role,
    RoleCreate,
    RolePermission,
    RolePermissionsUpdate,
    RoleUpdate,
    User,
)
from app.domains.identity.services import AccessControlService, RoleService


router = APIRouter()


@router.get(
    "/permission-catalog",
    response_model=PermissionCatalog,
    summary="Lấy catalog phân quyền",
)
async def get_permission_catalog(
    service: Annotated[AccessControlService, Depends(get_access_control_service)],
    _: Annotated[
        User,
        Depends(require_permission("Role-Based Access", "View")),
    ],
) -> PermissionCatalog:
    return service.get_catalog()


@router.get(
    "/{role_id}/permissions",
    response_model=list[RolePermission],
    summary="Lấy quyền của vai trò",
)
async def list_role_permissions(
    role_id: str,
    service: Annotated[AccessControlService, Depends(get_access_control_service)],
    _: Annotated[
        User,
        Depends(require_permission("Role-Based Access", "View")),
    ],
) -> list[RolePermission]:
    return service.list_role_permissions(role_id)


@router.put(
    "/{role_id}/permissions",
    response_model=list[RolePermission],
    summary="Thay thế quyền của vai trò",
)
async def replace_role_permissions(
    role_id: str,
    payload: RolePermissionsUpdate,
    service: Annotated[AccessControlService, Depends(get_access_control_service)],
    _: Annotated[
        User,
        Depends(require_permission("Role-Based Access", "Edit")),
    ],
) -> list[RolePermission]:
    return service.replace_role_permissions(role_id, payload.permission_ids)


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
    request: Request,
) -> Role:
    """Tạo role và ghi nhận user thực hiện vào dữ liệu audit."""

    created = service.create_role(payload, current_user.id)
    request.state.audit_resource_id = created.id
    return created


# READ — Lấy danh sách vai trò.
@router.get("/", response_model=list[Role], summary="Lấy danh sách vai trò")
async def list_roles(
    service: Annotated[RoleService, Depends(get_role_service)],
    _: Annotated[
        User,
        Depends(require_permission("Role-Based Access", "View")),
    ],
) -> list[Role]:
    """Trả danh sách role hiện có."""

    return service.list_roles()


# READ — Lấy vai trò theo ID.
@router.get(
    "/{role_id}",
    response_model=Role,
    summary="Lấy vai trò theo ID",
)
async def get_role(
    role_id: str,
    service: Annotated[RoleService, Depends(get_role_service)],
    _: Annotated[
        User,
        Depends(require_permission("Role-Based Access", "View")),
    ],
) -> Role:
    """Trả role tương ứng hoặc HTTP 404 nếu ID không tồn tại."""

    return service.get_role(role_id)


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


# DELETE chưa được triển khai trong phạm vi hiện tại.
