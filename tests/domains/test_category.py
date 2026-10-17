"""Category use-case và API tests thuộc Inventory domain."""

import asyncio

import httpx

from app.domains.inventory.routers.dependencies import get_category_service
from app.domains.inventory.schemas import Category
from app.domains.inventory.services import CategoryService
from app.main import app


class StubCategoryRepository:
    def __init__(self, categories: list[Category]) -> None:
        self._categories = categories

    def list(self) -> list[Category]:
        return [category.model_copy(deep=True) for category in self._categories]


def test_category_service_lists_categories() -> None:
    service = CategoryService(
        StubCategoryRepository(
            [
                Category(id="catg-0001", name="Router"),
                Category(id="catg-0002", name="Switch"),
            ]
        )
    )

    categories = service.list_categories()

    assert [category.name for category in categories] == ["Router", "Switch"]


def test_list_categories_api() -> None:
    service = CategoryService(
        StubCategoryRepository([Category(id="catg-0001", name="Router")])
    )

    async def override_category_service() -> CategoryService:
        return service

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/categories/")

        assert response.status_code == 200
        assert response.json() == [{"id": "catg-0001", "name": "Router"}]

    app.dependency_overrides[get_category_service] = override_category_service
    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.pop(get_category_service, None)
