"""API integration tests cho ba domain thử nghiệm."""

import asyncio
from uuid import uuid4

import httpx

from app.domains.conversation.routers.dependencies import (
    get_conversation_service,
    get_conversation_title_generator,
)
from app.domains.conversation.schemas import Conversation, Message
from app.domains.conversation.services import ConversationService
from app.domains.execution.routers.dependencies import get_execution_service
from app.domains.execution.schemas import Operation, Task
from app.domains.execution.services import ExecutionService
from app.domains.inventory.routers.dependencies import get_device_service
from app.domains.inventory.schemas import Device
from app.domains.inventory.services import DeviceService
from app.main import app
from app.domains.identity.routers.dependencies import get_identity_service
from app.domains.identity.schemas import User, UserRecord, UserStatus
from app.domains.identity.services import IdentityService
from app.domains.identity.utils import hash_password
from app.agents.dependencies import (
    get_analysis_orchestrator,
    get_execution_orchestrator,
    get_gns3_provider,
    get_planning_orchestrator,
)
from app.core.config import Settings
from datetime import UTC, datetime


class StubIdentityRepository:
    def __init__(self):
        now = datetime.now(UTC)
        self.user = UserRecord(
            id="user-test",
            role_id="role-test",
            email="test@example.com",
            password_hash=hash_password("test-password"),
            full_name="Test",
            user_status=UserStatus.ACTIVE,
            created_at=now,
        )
        self.sessions = {}

    def get_user_by_email(self, email):
        return self.user if email == self.user.email else None

    def get_user(self, user_id):
        return (
            User.model_validate(self.user.model_dump())
            if user_id == self.user.id
            else None
        )

    def get_user_with_password(self, user_id):
        return self.user if user_id == self.user.id else None

    def get_role(self, role_id):
        return None

    def get_permissions(self, role_id):
        return {
            ("Chatbot", "View"),
            ("Chatbot", "Add"),
            ("Device Management", "Add"),
            ("Device Management", "View"),
            ("Device Management", "Edit"),
            ("Task Management", "View"),
            ("Task Management", "Add"),
        }

    def save_session(self, session):
        self.sessions[session.id] = session

    def get_session_by_hash(self, token_hash):
        return next(
            (s for s in self.sessions.values() if s.refresh_token_hash == token_hash),
            None,
        )

    def revoke_session(self, session_id, revoked_at):
        self.sessions[session_id] = self.sessions[session_id].model_copy(
            update={"revoked_at": revoked_at}
        )

    def is_session_active(self, session_id):
        s = self.sessions.get(session_id)
        return bool(s and s.revoked_at is None and s.expires_at > datetime.now(UTC))

    def get_active_session(self, session_id):
        return (
            self.sessions.get(session_id)
            if self.is_session_active(session_id)
            else None
        )

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


class StubPlanningOrchestrator:
    async def plan_user_message(self, conversation, message):
        return None


async def override_planning_orchestrator() -> StubPlanningOrchestrator:
    return StubPlanningOrchestrator()


app.dependency_overrides[get_planning_orchestrator] = override_planning_orchestrator


class StubExecutionOrchestrator:
    async def execute_task(self, task):
        return []


async def override_execution_orchestrator() -> StubExecutionOrchestrator:
    return StubExecutionOrchestrator()


app.dependency_overrides[get_execution_orchestrator] = override_execution_orchestrator


class StubAnalysisOrchestrator:
    async def analyze_and_respond(self, task, results):
        return None


async def override_analysis_orchestrator() -> StubAnalysisOrchestrator:
    return StubAnalysisOrchestrator()


app.dependency_overrides[get_analysis_orchestrator] = override_analysis_orchestrator


class StubGNS3Provider:
    def check_server_available(self):
        return {"version": "test"}


async def override_gns3_provider() -> StubGNS3Provider:
    return StubGNS3Provider()


app.dependency_overrides[get_gns3_provider] = override_gns3_provider


class StubConversationTitleGenerator:
    async def generate(self, first_message: str) -> str:
        return f"Title: {first_message}"[:100]


async def override_conversation_title_generator() -> StubConversationTitleGenerator:
    return StubConversationTitleGenerator()


app.dependency_overrides[get_conversation_title_generator] = (
    override_conversation_title_generator
)


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


class StubConversationRepository:
    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[Message]] = {}

    def save_conversation(self, conversation: Conversation) -> None:
        self._conversations[conversation.id] = conversation.model_copy(deep=True)

    def create_with_first_message(
        self,
        conversation: Conversation,
        message: Message,
    ) -> None:
        self.save_conversation(conversation)
        self.save(message)

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    def list_conversations(self, user_id: str | None = None) -> list[Conversation]:
        values = self._conversations.values()
        return [item for item in values if user_id is None or item.user_id == user_id]

    def save(self, message: Message) -> None:
        self._messages.setdefault(message.conversation_id, []).append(message)

    def list_by_conversation(self, conversation_id: str) -> list[Message]:
        return list(self._messages.get(conversation_id, []))


class StubExecutionRepository:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._operations: dict[str, Operation] = {}

    def save_task(self, task: Task) -> None:
        self._tasks[task.id] = task

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[Task]:
        return list(self._tasks.values())

    def find_task_by_source_message(self, message_id: str) -> Task | None:
        return next(
            (
                task
                for task in self._tasks.values()
                if task.source_message_id == message_id
            ),
            None,
        )

    def save_operation(self, operation: Operation) -> None:
        self._operations[operation.id] = operation

    def get_operation(self, operation_id: str) -> Operation | None:
        return self._operations.get(operation_id)

    def list_operations(self, task_id: str) -> list[Operation]:
        return sorted(
            (
                operation
                for operation in self._operations.values()
                if operation.task_id == task_id
            ),
            key=lambda operation: operation.display_order,
        )


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
    repository = StubConversationRepository()
    service = ConversationService(repository, repository)

    async def override_conversation_service() -> ConversationService:
        return service

    async def scenario() -> None:
        started = await request(
            "POST",
            "/api/v1/conversations/messages",
            {"message": "Kiểm tra neighbor trên P1"},
        )
        assert started.status_code == 201
        conversation_id = started.json()["conversation"]["id"]
        assert started.json()["conversation"]["user_id"] == "user-test"
        assert started.json()["conversation"]["title"] == (
            "Title: Kiểm tra neighbor trên P1"
        )
        assert started.json()["message"]["message_type"] == "USER_REQUEST"

        detail = await request("GET", f"/api/v1/conversations/{conversation_id}")
        messages = await request(
            "GET",
            f"/api/v1/conversations/{conversation_id}/messages",
        )
        assert detail.status_code == 200
        assert detail.json()["messages"][0]["message"] == "Kiểm tra neighbor trên P1"
        assert messages.status_code == 200
        assert messages.json()[0]["conversation_id"] == conversation_id

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
    service = ExecutionService(StubExecutionRepository())

    async def override_execution_service() -> ExecutionService:
        return service

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

    app.dependency_overrides[get_execution_service] = override_execution_service
    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.pop(get_execution_service, None)
