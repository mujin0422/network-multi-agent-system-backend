"""Use cases cho resource Brand."""

from app.domains.audit.transaction import audit_mutation

from app.core.exceptions import ResourceNotFoundError
from app.core.utils import IdPrefix, generate_id
from app.domains.inventory.repositories import BrandRepository
from app.domains.inventory.schemas import Brand, BrandCreate, BrandUpdate
from app.domains.inventory.utils import ensure_unique_name


class BrandService:
    """Cung cấp các thao tác nghiệp vụ liên quan tới hãng thiết bị."""

    def __init__(self, repository: BrandRepository) -> None:
        self._repository = repository

    # =============================================================================
    # Brand — tạo, lấy và cập nhật hãng thiết bị
    # =============================================================================

    def create_brand(self, payload: BrandCreate) -> Brand:
        """Kiểm tra tên duy nhất, sinh ID và lưu Brand mới."""

        ensure_unique_name(
            self._repository.get_all(),
            payload.name,
            resource_label="brand",
        )
        brand = Brand(id=generate_id(IdPrefix.BRAND), **payload.model_dump())
        with audit_mutation("BRAND_CREATE", "BRAND", brand.id):
            self._repository.save(brand)
        return brand

    def list_brands(self) -> list[Brand]:
        """Lấy danh sách brand có thể dùng khi khai báo device."""

        return self._repository.get_all()

    def get_brand(self, brand_id: str) -> Brand:
        """Lấy một Brand theo ID hoặc phát sinh lỗi ánh xạ thành HTTP 404."""

        brand = self._repository.get_by_id(brand_id)
        if brand is None:
            raise ResourceNotFoundError(f"Không tìm thấy brand '{brand_id}'")
        return brand

    def update_brand(self, brand_id: str, payload: BrandUpdate) -> Brand:
        """Cập nhật các trường được gửi lên của một Brand đã tồn tại."""

        current = self.get_brand(brand_id)

        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        candidate = current.model_copy(update=changes)
        ensure_unique_name(
            self._repository.get_all(),
            candidate.name,
            resource_label="brand",
            exclude_id=brand_id,
        )
        with audit_mutation("BRAND_UPDATE", "BRAND", candidate.id):
            self._repository.save(candidate)
        return candidate

    # =============================================================================
    # Xác minh tên Brand
    # =============================================================================

    def _ensure_unique_name(
        self,
        name: str,
        exclude_brand_id: str | None = None,
    ) -> None:
        """Không cho phép hai Brand có cùng tên, không phân biệt hoa thường."""

        for brand in self._repository.get_all():
            if brand.id == exclude_brand_id:
                continue
            if brand.name.casefold() == name.casefold():
                raise ResourceConflictError(f"Tên brand '{name}' đã được sử dụng")
