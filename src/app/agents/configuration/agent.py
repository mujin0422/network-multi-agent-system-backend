"""Configuration Agent biên dịch yêu cầu WRITE thành CLI command."""

import asyncio
import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.configuration.prompts import CONFIGURATION_SYSTEM_PROMPT
from app.agents.configuration.schemas import GeneratedConfigurationSet
from app.agents.planner.agent import PlannerAgent
from app.domains.execution.schemas import AccessMode, ExecutionPlanCreate
from app.domains.inventory.schemas import Device
from app.tools.network.commands import normalize_config_commands


class ConfigurationAgent:

    name = "configuration-agent"

    def __init__(
        self,
        chat_model: Any,
        *,
        max_validation_retries: int = 2,
        timeout_seconds: float = 90.0,
    ) -> None:
        """Khởi tạo Configuration Agent với model chat, số lần retry và timeout."""
        self._model = chat_model
        self.max_validation_retries = max_validation_retries
        self.timeout_seconds = timeout_seconds


    async def generate(
        self,
        plan: ExecutionPlanCreate,
        devices: list[Device],
        interfaces_by_device_id: dict[str, list[str]],
    ) -> ExecutionPlanCreate:
        """Bổ sung command cho mọi WRITE operation mà không đổi cấu trúc plan."""

        # Bước 1: Xác định các Operation WRITE cần sinh cấu hình.
        write_orders = {
            order
            for order, operation in enumerate(plan.operations, 1)
            if any(item.access_mode == AccessMode.WRITE for item in operation.devices)
        }
        if not write_orders:
            return plan

        # Bước 2: Chuẩn bị inventory công khai và danh sách interface hợp lệ.
        inventory = [
            {
                "id": item.id,
                "hostname": item.hostname,
                "device_type": item.device_type,
                "interfaces": interfaces_by_device_id.get(item.id, []),
            }
            for item in devices
        ]
        operations = [
            {"operation_order": order, **operation.model_dump(mode="json")}
            for order, operation in enumerate(plan.operations, 1)
            if order in write_orders
        ]

        # Bước 3: Tạo prompt chỉ chứa các Operation WRITE và schema đầu ra.
        messages = [
            SystemMessage(content=CONFIGURATION_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"INVENTORY:\n{json.dumps(inventory, ensure_ascii=False)}"
                    f"\n\nWRITE OPERATIONS:\n{json.dumps(operations, ensure_ascii=False)}"
                )
            ),
        ]

        try:
            # Bước 4: Gọi LLM trong giới hạn timeout và validation retry.
            async with asyncio.timeout(self.timeout_seconds):
                for attempt in range(self.max_validation_retries + 1):
                    result = await self._model.ainvoke(messages)
                    try:
                        # Bước 5: Bóc và xác thực structured output của Agent.
                        payload = PlannerAgent._extract_json_payload(
                            getattr(result, "content", result)
                        )
                        generated = GeneratedConfigurationSet.model_validate(payload)
                        # Bước 6: Ghép CLI vào đúng Operation WRITE trong plan.
                        return self._merge(plan, generated, write_orders)
                    except ValueError as exc:
                        if attempt == self.max_validation_retries:
                            raise ValueError(
                                "Configuration Agent trả JSON command không hợp lệ"
                            ) from exc
                        messages.append(
                            HumanMessage(
                                content=f"JSON chưa hợp lệ: {exc}. Hãy sửa và chỉ trả JSON."
                            )
                        )
        except TimeoutError as exc:
            raise TimeoutError(
                f"Configuration Agent không phản hồi trong {self.timeout_seconds} giây"
            ) from exc
        raise RuntimeError("Configuration Agent không thể sinh command")

    @staticmethod
    def _merge(
        plan: ExecutionPlanCreate,
        generated: GeneratedConfigurationSet,
        expected_orders: set[int],
    ) -> ExecutionPlanCreate:
        """Ghép command đã sinh vào đúng WRITE operation trong kế hoạch."""

        # Bước 1: Từ chối operation_order bị trùng hoặc không khớp kế hoạch.
        orders = [item.operation_order for item in generated.configurations]
        if len(orders) != len(set(orders)):
            raise ValueError("Configuration Agent trả trùng operation_order")
        by_order = {item.operation_order: item for item in generated.configurations}
        if set(by_order) != expected_orders:
            raise ValueError(
                "Configuration Agent phải trả đúng một cấu hình cho mỗi WRITE operation"
            )

        # Bước 2: Giữ nguyên READ và chỉ cập nhật tham số của Operation WRITE.
        operations = []
        for order, operation in enumerate(plan.operations, 1):
            if order not in expected_orders:
                operations.append(operation)
                continue
            parameters = dict(operation.operation_parameters)
            parameters.pop("configuration_requirements", None)
            # Bước 3: Chuẩn hóa CLI và loại các lệnh quản lý phiên.
            parameters["commands"] = normalize_config_commands(by_order[order].commands)
            operations.append(
                operation.model_copy(update={"operation_parameters": parameters})
            )

        # Bước 4: Trả về kế hoạch mới với các Operation WRITE đã được bổ sung command.
        return plan.model_copy(update={"operations": operations})
