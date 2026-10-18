"""Use cases cho resource Brand."""

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.core.utils import generate_id
from app.domains.inventory.repositories import BrandRepository
from app.domains.inventory.schemas import Brand, BrandCreate, BrandUpdate


class BrandService:
    """Cung cấp các thao tác nghiệp vụ liên quan tới hãng thiết bị."""

    def __init__(self, repository: BrandRepository) -> None:
        self._repository = repository

    def create_brand(self, payload: BrandCreate) -> Brand:
        """Kiểm tra tên duy nhất, sinh ID và lưu Brand mới."""

        self._ensure_unique_name(payload.name)
        brand = Brand(id=generate_id("brnd"), **payload.model_dump())
        self._repository.save(brand)
        return brand

    def list_brands(self) -> list[Brand]:
        """Lấy danh sách brand có thể dùng khi khai báo device."""

        return self._repository.list()

    def get_brand(self, brand_id: str) -> Brand:
        """Lấy một Brand theo ID hoặc phát sinh lỗi ánh xạ thành HTTP 404."""

        brand = self._repository.get(brand_id)
        if brand is None:
            raise ResourceNotFoundError(f"Không tìm thấy brand '{brand_id}'")
        return brand

    def update_brand(self, brand_id: str, payload: BrandUpdate) -> Brand:
        """Cập nhật các trường được gửi lên của một Brand đã tồn tại."""

        current = self.get_brand(brand_id)

        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        candidate = current.model_copy(update=changes)
        self._ensure_unique_name(candidate.name, exclude_brand_id=brand_id)
        self._repository.save(candidate)
        return candidate

    def _ensure_unique_name(
        self,
        name: str,
        exclude_brand_id: str | None = None,
    ) -> None:
        """Không cho phép hai Brand có cùng tên, không phân biệt hoa thường."""

        for brand in self._repository.list():
            if brand.id == exclude_brand_id:
                continue
            if brand.name.casefold() == name.casefold():
                raise ResourceConflictError(f"Tên brand '{name}' đã được sử dụng")
