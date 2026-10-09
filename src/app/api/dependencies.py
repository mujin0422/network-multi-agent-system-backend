"""Dependency factories and application object composition."""

from functools import lru_cache

from app.agents.analyst import AnalystAgent
from app.agents.manager import AgentManager
from app.agents.network import NetworkAgent
from app.agents.registry import AgentRegistry
from app.core.config import get_settings
from app.domains.conversation import (
    ConversationService,
    InMemoryConversationRepository,
)
from app.domains.execution import ExecutionService, InMemoryExecutionRepository
from app.domains.inventory import (
    InMemoryDeviceRepository,
    InventoryService,
    PostgresDeviceRepository,
)
from app.domains.network.provider import DeviceConnectionProvider
from app.domains.network.repository import PostgresDeviceConfigRepository
from app.domains.network.service import NetworkService


@lru_cache
def _build_agent_manager() -> AgentManager:
    """Build the agent use case once for the lifetime of the API process."""
    registry = AgentRegistry([NetworkAgent(), AnalystAgent()])
    return AgentManager(registry=registry)


async def get_agent_manager() -> AgentManager:
    """Expose the cached manager without dispatching sync work to a thread pool."""
    return _build_agent_manager()


@lru_cache
def _build_network_service() -> NetworkService:
    """Build the network use case and inject its external provider."""
    settings = get_settings()
    repository = PostgresDeviceConfigRepository(
        database_url=settings.database_url,
        encryption_key=settings.device_credential_encryption_key,
    )
    provider = DeviceConnectionProvider(settings=settings, repository=repository)
    return NetworkService(provider=provider)


async def get_network_service() -> NetworkService:
    """Expose the cached service as an async FastAPI dependency."""
    return _build_network_service()


@lru_cache
def _build_conversation_service() -> ConversationService:
    """Dùng in-memory adapter để frontend có thể test API chưa cần database."""
    return ConversationService(InMemoryConversationRepository())


async def get_conversation_service() -> ConversationService:
    return _build_conversation_service()


@lru_cache
def _build_inventory_service() -> InventoryService:
    """Chọn repository theo môi trường mà không làm thay đổi API route."""
    settings = get_settings()
    if settings.inventory_repository_backend == "postgres":
        return InventoryService(PostgresDeviceRepository(settings.database_url))
    return InventoryService(InMemoryDeviceRepository())


async def get_inventory_service() -> InventoryService:
    return _build_inventory_service()


@lru_cache
def _build_execution_service() -> ExecutionService:
    """Khởi tạo stateful service dùng để thử Task/Operation/ChangeSet API."""
    return ExecutionService(InMemoryExecutionRepository())


async def get_execution_service() -> ExecutionService:
    return _build_execution_service()
