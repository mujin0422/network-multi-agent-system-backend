"""HTTP routes cho resource Brand."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.domains.inventory.routers.dependencies import get_brand_service
from app.domains.inventory.schemas import Brand, BrandCreate, BrandUpdate
from app.domains.inventory.services import BrandService


router = APIRouter()


# CREATE — Thêm một hãng thiết bị mới.
@router.post(
    "/",
    response_model=Brand,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm hãng thiết bị",
)
async def create_brand(
    payload: BrandCreate,
    service: Annotated[BrandService, Depends(get_brand_service)],
) -> Brand:
    """Tạo Brand mới sau khi kiểm tra tên không bị trùng."""

    return service.create_brand(payload)


# READ — Lấy danh sách hãng thiết bị và các driver được hỗ trợ.
@router.get("/", response_model=list[Brand], summary="Lấy danh sách hãng thiết bị")
async def list_brands(
    service: Annotated[BrandService, Depends(get_brand_service)],
) -> list[Brand]:
    """Trả danh sách brand dùng khi tạo hoặc cập nhật device."""

    return service.list_brands()


# READ — Lấy chi tiết một hãng thiết bị theo ID.
@router.get(
    "/{brand_id}",
    response_model=Brand,
    summary="Lấy hãng thiết bị theo ID",
)
async def get_brand(
    brand_id: str,
    service: Annotated[BrandService, Depends(get_brand_service)],
) -> Brand:
    """Trả Brand tương ứng hoặc HTTP 404 nếu ID không tồn tại."""

    return service.get_brand(brand_id)


# UPDATE — Sửa tên hoặc danh sách driver của một Brand theo ID.
@router.patch(
    "/{brand_id}",
    response_model=Brand,
    summary="Cập nhật hãng thiết bị",
)
async def update_brand(
    brand_id: str,
    payload: BrandUpdate,
    service: Annotated[BrandService, Depends(get_brand_service)],
) -> Brand:
    """Chỉ cập nhật các trường được gửi và giữ nguyên trường còn lại."""

    return service.update_brand(brand_id, payload)


# DELETE chưa được triển khai vì Brand có thể đang được bảng devices tham chiếu.
