"""API integration tests cho ba domain thử nghiệm."""

import asyncio
from uuid import uuid4

import httpx

from app.domains.conversation.repositories import InMemoryConversationRepository
from app.domains.conversation.routers.dependencies import get_conversation_service
from app.domains.conversation.services import ConversationService
from app.domains.inventory.routers.dependencies import get_device_service
from app.domains.inventory.schemas import Device
from app.domains.inventory.services import DeviceService
from app.main import app
from app.domains.identity.routers.dependencies import get_identity_service
from app.domains.identity.schemas import User, UserRecord, UserStatus
from app.domains.identity.services import IdentityService
from app.core.config import Settings
from datetime import UTC, datetime


class StubIdentityRepository:
    def __init__(self):
        now = datetime.now(UTC)
        self.user = UserRecord(
            id="user-test", role_id="role-test", email="test@example.com",
            password_hash=IdentityService.hash_password("test-password"),
            full_name="Test", user_status=UserStatus.ACTIVE, created_at=now,
        )
        self.sessions = {}

    def get_user_by_email(self, email):
        return self.user if email == self.user.email else None

    def get_user(self, user_id):
        return User.model_validate(self.user.model_dump()) if user_id == self.user.id else None

    def get_user_with_password(self, user_id):
        return self.user if user_id == self.user.id else None

    def get_role(self, role_id):
        return None

    def get_permissions(self, role_id):
        return {
            ("Chatbot", "View"), ("Chatbot", "Execute"),
            ("Device Management", "Add"), ("Device Management", "View"),
            ("Device Management", "Edit"), ("Task Management", "View"),
            ("Task Management", "Execute"),
        }

    def save_session(self, session):
        self.sessions[session.id] = session

    def get_session_by_hash(self, token_hash):
        return next((s for s in self.sessions.values() if s.refresh_token_hash == token_hash), None)

    def revoke_session(self, session_id, revoked_at):
        self.sessions[session_id] = self.sessions[session_id].model_copy(update={"revoked_at": revoked_at})

    def is_session_active(self, session_id):
        s = self.sessions.get(session_id)
        return bool(s and s.revoked_at is None and s.expires_at > datetime.now(UTC))

    def get_active_session(self, session_id):
        return self.sessions.get(session_id) if self.is_session_active(session_id) else None

    def rotate_session(self, session_id, revoked_at, replacement):
        if not self.is_session_active(session_id):
            return False
        self.revoke_session(session_id, revoked_at)
        self.save_session(replacement)
        return True

    def update_login(self, user_id, logged_in_at):
        self.user = self.user.model_copy(update={"last_login_at": logged_in_at})


TEST_IDENTITY_REPOSITORY = StubIdentityRepository()
TEST_IDENTITY_SERVICE = IdentityService(
    TEST_IDENTITY_REPOSITORY, Settings(auth_jwt_secret="test-only-secret")
)


async def override_identity_service() -> IdentityService:
    return TEST_IDENTITY_SERVICE


app.dependency_overrides[get_identity_service] = override_identity_service


class StubDeviceRepository:
    def __init__(self) -> None:
        self._devices: dict[str, Device] = {}

    def save(self, device: Device) -> None:
        self._devices[device.id] = device.model_copy(deep=True)

    def get(self, device_id: str) -> Device | None:
        device = self._devices.get(device_id)
        return device.model_copy(deep=True) if device else None

    def get_by_hostname(self, hostname: str) -> Device | None:
        for device in self._devices.values():
            if device.hostname.casefold() == hostname.casefold():
                return device.model_copy(deep=True)
        return None

    def list(self) -> list[Device]:
        return [device.model_copy(deep=True) for device in self._devices.values()]


async def request(method: str, path: str, json: dict | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "test-password"},
        )
        token = response.json()["access_token"]
        return await client.request(
            method, path, json=json, headers={"Authorization": f"Bearer {token}"}
        )


def test_conversation_api_keeps_messages_in_the_parent_conversation() -> None:
    service = ConversationService(InMemoryConversationRepository())

    async def override_conversation_service() -> ConversationService:
        return service

    async def scenario() -> None:
        created = await request(
            "POST",
            "/api/v1/conversations/",
            {"user_id": "user-test", "title": "Kiểm tra OSPF"},
        )
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        message = await request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/messages",
            {"sender_by": "USER", "message": "Kiểm tra neighbor trên P1"},
        )
        assert message.status_code == 201

        detail = await request("GET", f"/api/v1/conversations/{conversation_id}")
        assert detail.status_code == 200
        assert detail.json()["messages"][0]["message"] == "Kiểm tra neighbor trên P1"

    app.dependency_overrides[get_conversation_service] = override_conversation_service
    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.pop(get_conversation_service, None)


def test_inventory_api_enforces_hostname_uniqueness() -> None:
    service = DeviceService(StubDeviceRepository())

    async def override_device_service() -> DeviceService:
        return service

    async def scenario() -> None:
        suffix = uuid4().hex[:8]
        payload = {
            "brand_id": "brnd-cisco",
            "category_id": "catg-router",
            "hostname": f"R-{suffix}",
            "host": "192.0.2.10",
            "port": int(suffix[:4], 16) % 50000 + 1024,
            "device_type": "cisco_ios",
            "last_updated_by": "user-test",
        }
        created = await request("POST", "/api/v1/devices/", payload)
        duplicate = await request(
            "POST",
            "/api/v1/devices/",
            {**payload, "host": "192.0.2.11", "port": payload["port"] + 1},
        )
        found_by_hostname = await request(
            "GET",
            f"/api/v1/devices/by-hostname/{payload['hostname'].lower()}",
        )

        assert created.status_code == 201
        assert duplicate.status_code == 409
        assert "Hostname" in duplicate.json()["detail"]
        assert found_by_hostname.status_code == 200
        assert found_by_hostname.json()["id"] == created.json()["id"]

    app.dependency_overrides[get_device_service] = override_device_service
    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.pop(get_device_service, None)


def test_execution_api_creates_task_and_operation() -> None:
    async def scenario() -> None:
        source_message_id = f"mesg-test-{uuid4().hex}"
        task_response = await request(
            "POST",
            "/api/v1/tasks/",
            {
                "conversation_id": "cons-test",
                "source_message_id": source_message_id,
                "user_id": "user-test",
                "input_message": "Cấu hình OSPF trên P3",
            },
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]

        operation_response = await request(
            "POST",
            f"/api/v1/tasks/{task_id}/operations",
            {
                "operation_intent": "CONFIGURE_OSPF",
                "display_order": 1,
                "operation_parameters": {"process_id": 1},
            },
        )
        assert operation_response.status_code == 201
        assert operation_response.json()["task_id"] == task_id
        assert operation_response.json()["operation_intent"] == "CONFIGURE_OSPF"

        detail_response = await request("GET", f"/api/v1/tasks/{task_id}")
        assert detail_response.status_code == 200
        assert len(detail_response.json()["operations"]) == 1

    asyncio.run(scenario())
