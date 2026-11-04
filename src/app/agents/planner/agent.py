"""Planner Agent chuyển yêu cầu người dùng thành execution plan có cấu trúc."""

import asyncio
import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.planner.prompts import PLANNER_SYSTEM_PROMPT
from app.domains.execution.schemas import ExecutionPlanCreate
from app.domains.inventory.schemas import Device
from app.tools.network.commands import normalize_config_commands


class PlannerAgent:
    name = "planner-agent"

    def __init__(
        self,
        chat_model: Any,
        max_validation_retries: int = 2,
        timeout_seconds: float = 90.0,
    ) -> None:
        # Gọi model theo chế độ chat thông thường. Không dùng
        # ``with_structured_output`` vì một số NVIDIA NIM không hỗ trợ tham số
        # ``guided_json`` do LangChain tự động gửi lên endpoint.
        self._planner = chat_model
        self.max_validation_retries = max_validation_retries
        self.timeout_seconds = timeout_seconds

    async def plan(
        self,
        user_message: str,
        devices: list[Device],
        node_interfaces: dict[str, list[str]] | None = None,
    ) -> ExecutionPlanCreate:
        """Tạo DAG operation chỉ với những device có trong inventory."""

        node_interfaces = node_interfaces or {}
        inventory = [
            {
                "id": device.id,
                "hostname": device.hostname,
                "brand_id": device.brand_id,
                "category_id": device.category_id,
                "device_type": device.device_type,
                "location": device.location,
                "interfaces": node_interfaces.get(device.hostname, []),
            }
            for device in devices
        ]
        prompt = (
            f"USER REQUEST:\n{user_message}\n\n"
            "AVAILABLE DEVICES (use only their id values):\n"
            f"{json.dumps(inventory, ensure_ascii=False)}\n\n"
            "RESPONSE JSON SCHEMA:\n"
            f"{json.dumps(ExecutionPlanCreate.model_json_schema(), ensure_ascii=False)}\n\n"
            "Chỉ trả về một JSON object hợp lệ theo schema trên. "
            "Không dùng Markdown và không thêm nội dung giải thích bên ngoài JSON."
        )
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        try:
            async with asyncio.timeout(self.timeout_seconds):
                for retry_number in range(self.max_validation_retries + 1):
                    result = await self._planner.ainvoke(messages)
                    try:
                        plan = self._parse_plan(result)
                        self._validate_interface_commands(
                            plan,
                            {
                                device.id: node_interfaces.get(device.hostname, [])
                                for device in devices
                            },
                        )
                        return plan
                    except ValueError as exc:
                        if retry_number == self.max_validation_retries:
                            raise

                        # Đưa cả kết quả sai và lỗi validation về cho model để
                        # model sửa JSON mà không phải mất ngữ cảnh ban đầu.
                        messages.append(
                            HumanMessage(
                                content=self._build_correction_prompt(result, exc),
                            )
                        )
        except TimeoutError as exc:
            raise TimeoutError(
                f"Planner Agent không phản hồi trong {self.timeout_seconds} giây"
            ) from exc

        raise RuntimeError("Planner Agent không thể tạo execution plan")

    @staticmethod
    def _build_correction_prompt(result: Any, error: ValueError) -> str:
        """Yêu cầu model sửa phản hồi không vượt qua validation."""

        invalid_content = getattr(result, "content", result)
        validation_error = error.__cause__ or error
        return (
            "JSON trước đó không hợp lệ. Hãy sửa và chỉ trả về JSON object hoàn chỉnh.\n\n"
            f"VALIDATION ERROR:\n{validation_error}\n\n"
            f"INVALID JSON:\n{invalid_content}\n\n"
            "Nhắc lại: operation có devices phải chứa operation_parameters.command "
            "là chuỗi không rỗng hoặc operation_parameters.commands là danh sách "
            "command không rỗng."
        )

    @staticmethod
    def _parse_plan(result: Any) -> ExecutionPlanCreate:
        """Bóc JSON thường từ phản hồi của model rồi kiểm tra bằng Pydantic."""

        try:
            content = getattr(result, "content", result)
            if isinstance(content, dict):
                plan = ExecutionPlanCreate.model_validate(content)
                return PlannerAgent._normalize_write_commands(plan)
            if not isinstance(content, str):
                raise ValueError("Planner Agent không trả về nội dung JSON dạng text")

            raw_json = content.strip()
            if raw_json.startswith("```") and raw_json.endswith("```"):
                lines = raw_json.splitlines()
                raw_json = "\n".join(lines[1:-1]).strip()

            plan = ExecutionPlanCreate.model_validate_json(raw_json)
            return PlannerAgent._normalize_write_commands(plan)
        except (ValidationError, ValueError) as exc:
            raise ValueError(
                "Planner Agent trả về JSON không đúng ExecutionPlanCreate"
            ) from exc

    @staticmethod
    def _normalize_write_commands(plan: ExecutionPlanCreate) -> ExecutionPlanCreate:
        """Lưu đúng payload sẽ được Netmiko thực thi vào approval snapshot."""

        normalized_operations = []
        for operation in plan.operations:
            if not any(device.access_mode.value == "WRITE" for device in operation.devices):
                normalized_operations.append(operation)
                continue

            parameters = dict(operation.operation_parameters)
            raw_commands = parameters.pop("commands", parameters.pop("command", None))
            commands = [raw_commands] if isinstance(raw_commands, str) else raw_commands
            if not isinstance(commands, list):
                raise ValueError("Operation WRITE không chứa danh sách command hợp lệ")
            parameters["commands"] = normalize_config_commands(commands)
            normalized_operations.append(
                operation.model_copy(update={"operation_parameters": parameters})
            )
        return plan.model_copy(update={"operations": normalized_operations})

    @staticmethod
    def _validate_interface_commands(
        plan: ExecutionPlanCreate,
        interfaces_by_device_id: dict[str, list[str]],
    ) -> None:
        """Không cho phép WRITE dùng tên interface vật lý không có trong GNS3."""

        physical_interface = re.compile(
            r"^interface\s+((?:Fast|Gigabit|TenGigabit|TwentyFiveGigabit|FortyGigabit|HundredGigabit)?Ethernet\S+)$",
            flags=re.IGNORECASE,
        )
        for operation in plan.operations:
            write_devices = [
                device for device in operation.devices if device.access_mode.value == "WRITE"
            ]
            if not write_devices:
                continue
            commands = operation.operation_parameters.get("commands", [])
            for command in commands:
                match = physical_interface.fullmatch(command.strip())
                if match is None:
                    continue
                interface_name = match.group(1).split(".", maxsplit=1)[0]
                for device in write_devices:
                    available = interfaces_by_device_id.get(device.device_id, [])
                    if available and interface_name not in available:
                        raise ValueError(
                            f"Interface '{interface_name}' không tồn tại trên "
                            f"device '{device.device_id}'. Interface hợp lệ: "
                            f"{', '.join(available)}"
                        )
