"""Use cases cho resource Category."""

from app.domains.inventory.repositories import CategoryRepository
from app.domains.inventory.schemas import Category


class CategoryService:
    """Cung cấp các thao tác nghiệp vụ liên quan tới loại thiết bị."""

    def __init__(self, repository: CategoryRepository) -> None:
        self._repository = repository

    def list_categories(self) -> list[Category]:
        """Lấy danh sách Category có thể dùng khi khai báo Device."""

        return self._repository.list()
