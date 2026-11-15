"""Điều phối việc chuyển yêu cầu WRITE thành CLI đã được kiểm tra."""

from datetime import UTC, datetime

from app.agents.configuration import ConfigurationAgent
from app.agents.planner import PlannerAgent
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventStatus,
    ActivityEventType,
    ExecutionPlanCreate,
)
from app.domains.execution.services import ExecutionService
from app.domains.inventory.schemas import Device


class ConfigurationOrchestrator:
    """Điều phối Configuration Agent và các kiểm tra trước khi lưu kế hoạch."""

    def __init__(
        self,
        configuration_agent: ConfigurationAgent,
        execution_service: ExecutionService,
    ) -> None:
        """Khởi tạo thành phần sinh cấu hình và dịch vụ ghi activity."""

        self._configuration_agent = configuration_agent
        self._execution_service = execution_service

    async def configure_plan(
        self,
        task_id: str,
        plan: ExecutionPlanCreate,
        devices: list[Device],
        interfaces_by_device_id: dict[str, list[str]],
    ) -> ExecutionPlanCreate:
        """Sinh và kiểm tra CLI cho các WRITE operation trong kế hoạch."""

        # Bước 1: Xác định số WRITE operation cần Configuration Agent xử lý.
        write_operation_count = sum(
            1
            for operation in plan.operations
            if any(device.access_mode.value == "WRITE" for device in operation.devices)
        )
        if not write_operation_count:
            return plan

        # Bước 2: Ghi activity bắt đầu để frontend hiển thị đúng trình tự.
        configuration_started_at = datetime.now(UTC)
        self._execution_service.record_activity(
            task_id,
            ActivityActorType.CONFIGURATION,
            ActivityEventType.CONFIGURATION_STARTED,
            ActivityEventStatus.RUNNING,
            event_data={"operation_count": write_operation_count},
            started_at=configuration_started_at,
        )

        # Bước 3: Gọi Configuration Agent sinh CLI từ yêu cầu WRITE.
        configured_plan = await self._configuration_agent.generate(
            plan,
            devices,
            interfaces_by_device_id,
        )

        # Bước 4: Đối chiếu interface trong CLI với inventory GNS3.
        PlannerAgent._validate_interface_commands(
            configured_plan,
            interfaces_by_device_id,
        )

        # Bước 5: Ghi activity hoàn tất sau khi CLI vượt qua validation.
        self._execution_service.record_activity(
            task_id,
            ActivityActorType.CONFIGURATION,
            ActivityEventType.CONFIGURATION_COMPLETED,
            event_data={"operation_count": write_operation_count},
            started_at=configuration_started_at,
        )
        return configured_plan
