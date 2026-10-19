"""HTTP routes quản lý tài khoản người dùng."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.domains.identity.routers.dependencies import (
    get_user_service,
    require_permission,
)
from app.domains.identity.schemas import User, UserCreate, UserUpdate
from app.domains.identity.services import UserService


router = APIRouter()


# CREATE — Thêm tài khoản người dùng mới.
@router.post(
    "/",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm người dùng",
)
async def create_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_permission("User Management", "Add"))],
) -> User:
    """Tạo user sau khi kiểm tra role và email không trùng."""

    return service.create_user(payload)


# UPDATE — Sửa tài khoản người dùng theo ID.
@router.patch(
    "/{user_id}",
    response_model=User,
    summary="Cập nhật người dùng",
)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(require_permission("User Management", "Edit"))],
) -> User:
    """Chỉ cập nhật các trường được gửi; password luôn được hash trước khi lưu."""

    return service.update_user(user_id, payload)


# READ và DELETE chưa được triển khai trong phạm vi hiện tại.
