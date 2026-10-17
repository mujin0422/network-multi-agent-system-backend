"""Brand use-case và API tests thuộc Inventory domain."""

import asyncio

import httpx
import pytest

from app.core.exceptions import ResourceConflictError
from app.domains.inventory.routers.dependencies import get_brand_service
from app.domains.inventory.schemas import Brand, BrandCreate, BrandUpdate
from app.domains.inventory.services import BrandService
from app.main import app


class StubBrandRepository:
    def __init__(self, brands: list[Brand]) -> None:
        self._brands = brands

    def save(self, brand: Brand) -> None:
        for index, current in enumerate(self._brands):
            if current.id == brand.id:
                self._brands[index] = brand.model_copy(deep=True)
                return
        self._brands.append(brand.model_copy(deep=True))

    def get(self, brand_id: str) -> Brand | None:
        for brand in self._brands:
            if brand.id == brand_id:
                return brand.model_copy(deep=True)
        return None

    def list(self) -> list[Brand]:
        return [brand.model_copy(deep=True) for brand in self._brands]


def test_brand_service_lists_brands_in_stable_order() -> None:
    repository = StubBrandRepository(
        [
            Brand(
                id="brnd-0001",
                name="Cisco",
                supported_drivers=["cisco_ios", "cisco_ios_telnet"],
            ),
            Brand(
                id="brnd-0002",
                name="MikroTik",
                supported_drivers=["mikrotik_routeros"],
            ),
        ]
    )

    brands = BrandService(repository).list_brands()

    assert [brand.name for brand in brands] == ["Cisco", "MikroTik"]
    assert brands[0].supported_drivers == ["cisco_ios", "cisco_ios_telnet"]
    assert BrandService(repository).get_brand("brnd-0001").name == "Cisco"


def test_brand_service_creates_and_updates_brand() -> None:
    service = BrandService(StubBrandRepository([]))

    created = service.create_brand(
        BrandCreate(name="Juniper", supported_drivers=["juniper_junos"])
    )
    updated = service.update_brand(
        created.id,
        BrandUpdate(supported_drivers=["juniper_junos", "juniper_screenos"]),
    )

    assert created.id.startswith("brnd-")
    assert updated.name == "Juniper"
    assert updated.supported_drivers == ["juniper_junos", "juniper_screenos"]


def test_brand_service_rejects_duplicate_name() -> None:
    service = BrandService(
        StubBrandRepository(
            [Brand(id="brnd-0001", name="Cisco", supported_drivers=["cisco_ios"])]
        )
    )

    with pytest.raises(ResourceConflictError):
        service.create_brand(BrandCreate(name="cisco", supported_drivers=[]))


def test_list_brands_api() -> None:
    service = BrandService(
        StubBrandRepository(
            [Brand(id="brnd-0001", name="Cisco", supported_drivers=["cisco_ios"])]
        )
    )

    async def override_brand_service() -> BrandService:
        return service

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/brands/")
            detail = await client.get("/api/v1/brands/brnd-0001")

            created = await client.post(
                "/api/v1/brands/",
                json={"name": "Juniper", "supported_drivers": ["juniper_junos"]},
            )
            brand_id = created.json()["id"]
            updated = await client.patch(
                f"/api/v1/brands/{brand_id}",
                json={"supported_drivers": ["juniper_junos", "juniper_screenos"]},
            )

        assert response.status_code == 200
        assert detail.status_code == 200
        assert detail.json()["name"] == "Cisco"
        assert response.json() == [
            {
                "id": "brnd-0001",
                "name": "Cisco",
                "supported_drivers": ["cisco_ios"],
            }
        ]
        assert created.status_code == 201
        assert updated.status_code == 200
        assert updated.json()["name"] == "Juniper"
        assert updated.json()["supported_drivers"] == [
            "juniper_junos",
            "juniper_screenos",
        ]

    app.dependency_overrides[get_brand_service] = override_brand_service
    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.pop(get_brand_service, None)
