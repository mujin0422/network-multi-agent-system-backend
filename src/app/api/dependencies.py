"""Dependency factories and application object composition."""

from functools import lru_cache

from app.agents.analyst import AnalystAgent
from app.agents.manager import AgentManager
from app.agents.network import NetworkAgent
from app.agents.registry import AgentRegistry
from app.core.config import get_settings
from app.domains.network.provider import DeviceConnectionProvider
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
    provider = DeviceConnectionProvider(settings=get_settings())
    return NetworkService(provider=provider)


async def get_network_service() -> NetworkService:
    """Expose the cached service as an async FastAPI dependency."""
    return _build_network_service()
