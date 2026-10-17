"""Credential use-case và API tests thuộc Inventory domain."""

import asyncio
from datetime import UTC, datetime

import httpx

from app.domains.inventory.routers.dependencies import get_credential_service
from app.domains.inventory.schemas import Credential, CredentialCreate, CredentialUpdate
from app.domains.inventory.services import CredentialService
from app.main import app


class StubCredentialRepository:
    def __init__(self, credentials: list[Credential] | None = None) -> None:
        self._credentials = {
            credential.id: credential.model_copy(deep=True)
            for credential in credentials or []
        }
        self.password: str | None = None
        self.secret: str | None = None

    def create(
        self,
        credential: Credential,
        password: str,
        secret: str | None,
    ) -> None:
        self._credentials[credential.id] = credential.model_copy(deep=True)
        self.password = password
        self.secret = secret

    def update(
        self,
        credential: Credential,
        password: str | None,
        secret: str | None,
        update_password: bool,
        update_secret: bool,
    ) -> None:
        self._credentials[credential.id] = credential.model_copy(deep=True)
        if update_password:
            self.password = password
        if update_secret:
            self.secret = secret

    def get(self, credential_id: str) -> Credential | None:
        credential = self._credentials.get(credential_id)
        return credential.model_copy(deep=True) if credential else None

    def list(self) -> list[Credential]:
        return [item.model_copy(deep=True) for item in self._credentials.values()]


def test_credential_service_crud_without_exposing_secrets() -> None:
    repository = StubCredentialRepository()
    service = CredentialService(repository)

    created = service.create_credential(
        CredentialCreate(
            name="GNS3 Lab",
            username="admin",
            password="password-value",
            secret="enable-secret",
            created_by="user-admin",
        )
    )
    updated = service.update_credential(
        created.id,
        CredentialUpdate(username="netops", last_updated_by="user-admin"),
    )

    assert service.get_credential(created.id).id == created.id
    assert service.list_credentials()[0].id == created.id
    assert updated.username == "netops"
    assert repository.password == "password-value"
    assert repository.secret == "enable-secret"
    assert "password" not in created.model_dump()
    assert "secret" not in created.model_dump()


def test_credential_api_lists_gets_creates_and_updates() -> None:
    now = datetime.now(UTC)
    repository = StubCredentialRepository(
        [
            Credential(
                id="cred-0001",
                name="Existing Lab",
                username="admin",
                encryption_type="PGP_SYM_AES256",
                created_by="user-admin",
                last_updated_by="user-admin",
                created_at=now,
                last_updated_at=now,
            )
        ]
    )
    service = CredentialService(repository)

    async def override_credential_service() -> CredentialService:
        return service

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            listed = await client.get("/api/v1/credentials/")
            detail = await client.get("/api/v1/credentials/cred-0001")
            created = await client.post(
                "/api/v1/credentials/",
                json={
                    "name": "New Lab",
                    "username": "netops",
                    "password": "private-password",
                    "secret": "private-secret",
                    "created_by": "user-admin",
                },
            )
            credential_id = created.json()["id"]
            updated = await client.patch(
                f"/api/v1/credentials/{credential_id}",
                json={"description": "Updated", "last_updated_by": "user-admin"},
            )

        assert listed.status_code == 200
        assert detail.status_code == 200
        assert created.status_code == 201
        assert updated.status_code == 200
        assert updated.json()["description"] == "Updated"
        assert "password" not in created.json()
        assert "secret" not in created.json()

    app.dependency_overrides[get_credential_service] = override_credential_service
    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.pop(get_credential_service, None)
