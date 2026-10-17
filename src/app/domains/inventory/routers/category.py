"""HTTP routes cho resource Category."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.domains.inventory.routers.dependencies import get_category_service
from app.domains.inventory.schemas import Category
from app.domains.inventory.services import CategoryService


router = APIRouter()


# READ — Lấy danh sách loại thiết bị.
@router.get(
    "/",
    response_model=list[Category],
    summary="Lấy danh sách loại thiết bị",
)
async def list_categories(
    service: Annotated[CategoryService, Depends(get_category_service)],
) -> list[Category]:
    """Trả danh sách Category dùng khi tạo hoặc cập nhật Device."""

    return service.list_categories()


# CREATE, UPDATE và DELETE Category chưa được expose qua API.
