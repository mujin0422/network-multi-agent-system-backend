"""Dependency composition for internal agent orchestration."""

from functools import lru_cache

from langchain_nvidia_ai_endpoints import ChatNVIDIA

from app.agents.network import NetworkAgent
from app.agents.orchestrator import ExecutionOrchestrator, PlanningOrchestrator
from app.agents.planner import PlannerAgent
from app.core.config import get_settings
from app.domains.execution.repositories import ExecutionRepository
from app.domains.execution.services import ExecutionService
from app.domains.inventory.providers import DeviceConnectionProvider, GNS3Provider
from app.domains.inventory.repositories import (
    DeviceConfigRepository,
    DeviceRepository,
)
from app.domains.inventory.services import DeviceService, NetworkService
from app.tools import NetmikoNetworkTool, NetworkTool, NornirNetworkTool


@lru_cache
def _build_gns3_provider() -> GNS3Provider:
    """Khởi tạo provider chỉ dùng để kiểm tra GNS3 Server."""

    return GNS3Provider(get_settings())


async def get_gns3_provider() -> GNS3Provider:
    """FastAPI dependency cung cấp GNS3 availability provider."""

    return _build_gns3_provider()


@lru_cache
def _build_planner_agent() -> PlannerAgent:
    """Khởi tạo Planner Agent cùng NVIDIA chat model."""

    # Bước 1: Dừng sớm nếu thiếu cấu hình bắt buộc của AI provider.
    settings = get_settings()
    if not settings.nvidia_api_key or not settings.nvidia_model:
        raise RuntimeError(
            "NVIDIA_API_KEY và NVIDIA_MODEL phải được cấu hình để chạy Planner Agent"
        )

    # Bước 2: temperature=0 giúp kế hoạch ổn định hơn cho cùng một input.
    chat_model = ChatNVIDIA(
        model=settings.nvidia_model,
        api_key=settings.nvidia_api_key,
        temperature=0,
    )

    # Bước 3: Planner Agent chỉ biết chat model, không biết database hay FastAPI.
    return PlannerAgent(chat_model)


@lru_cache
def _build_planning_orchestrator() -> PlanningOrchestrator:
    """Lắp toàn bộ dependency cho luồng USER message -> execution plan."""

    # Bước 1: Lấy cấu hình database dùng để lắp các domain service.
    settings = get_settings()

    # Bước 2: Domain service được lắp với PostgreSQL adapter tương ứng.
    execution_service = ExecutionService(ExecutionRepository(settings.database_url))
    device_service = DeviceService(DeviceRepository(settings.database_url))

    # Bước 3: Dùng lại Planner Agent đã được cache. Orchestrator nhận tất cả thành phần qua constructor để có thể thay bằng stub trong unit test.
    return PlanningOrchestrator(
        _build_planner_agent(),
        execution_service,
        device_service,
    )


async def get_planning_orchestrator() -> PlanningOrchestrator:
    """FastAPI dependency cung cấp PlanningOrchestrator đã được cache."""

    return _build_planning_orchestrator()


@lru_cache
def _build_network_agent() -> NetworkAgent:
    """Lắp Network Agent với backend Netmiko hoặc Nornir theo cấu hình."""

    # Bước 1: Repository này là nơi duy nhất đọc và giải mã credential thiết bị.
    settings = get_settings()
    credential_repository = DeviceConfigRepository(
        database_url=settings.database_url,
        encryption_key=settings.device_credential_encryption_key,
    )
    # Bước 2: Provider/Service che giấu chi tiết credential và connection khỏi Agent.
    provider = DeviceConnectionProvider(settings, credential_repository)
    network_service = NetworkService(provider)

    # Bước 3: Cả hai backend cùng tuân theo NetworkTool contract. Vì vậy NetworkAgent không cần biết đang chạy trực tiếp bằng Netmiko hay qua Nornir.
    tool: NetworkTool
    if settings.network_backend == "nornir":
        tool = NornirNetworkTool(network_service, settings.nornir_num_workers)
    else:
        tool = NetmikoNetworkTool(network_service)
    # Bước 4: Inject backend đã chọn vào execution-only Network Agent.
    return NetworkAgent(tool)


async def get_network_agent() -> NetworkAgent:
    """FastAPI dependency cung cấp NetworkAgent đã được cache."""

    return _build_network_agent()


@lru_cache
def _build_execution_orchestrator() -> ExecutionOrchestrator:
    """Lắp luồng Operation -> NetworkAgent -> thiết bị mạng."""

    # Execution Orchestrator dùng domain service để đọc kế hoạch và dùng lại
    # singleton NetworkAgent đã được cấu hình backend ở trên.
    settings = get_settings()
    execution_service = ExecutionService(ExecutionRepository(settings.database_url))
    return ExecutionOrchestrator(execution_service, _build_network_agent())


async def get_execution_orchestrator() -> ExecutionOrchestrator:
    """FastAPI dependency cung cấp ExecutionOrchestrator đã được cache."""

    return _build_execution_orchestrator()
