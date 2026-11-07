"""Planner Agent chuyển yêu cầu người dùng thành execution plan có cấu trúc."""

import asyncio
import ast
import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.planner.prompts import PLANNER_SYSTEM_PROMPT
from app.diagnostics import select_playbooks
from app.domains.execution.schemas import ExecutionPlanCreate, TaskType
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
        topology_neighbors: dict[str, list[dict[str, str]]] | None = None,
    ) -> ExecutionPlanCreate:
        """Tạo DAG operation chỉ với những device có trong inventory."""

        node_interfaces = node_interfaces or {}
        topology_neighbors = topology_neighbors or {}
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
        diagnostic_playbooks = [
            playbook.planner_payload() for playbook in select_playbooks(user_message)
        ]
        prompt = (
            f"USER REQUEST:\n{user_message}\n\n"
            "AVAILABLE DEVICES (use only their id values):\n"
            f"{json.dumps(inventory, ensure_ascii=False)}\n\n"
            "AVAILABLE TOPOLOGY NEIGHBORS (hostname and both link interfaces):\n"
            f"{json.dumps(topology_neighbors, ensure_ascii=False)}\n\n"
            "MATCHED DIAGNOSTIC PLAYBOOKS "
            "(for DIAGNOSIS, collect their required READ evidence; fill placeholders "
            "only with interfaces from AVAILABLE DEVICES):\n"
            f"{json.dumps(diagnostic_playbooks, ensure_ascii=False)}\n\n"
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
                        plan = self._parse_plan(
                            result,
                            default_task_type=(
                                TaskType.DIAGNOSIS if diagnostic_playbooks else None
                            ),
                        )
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
            "CẤU TRÚC TỐI THIỂU BẮT BUỘC:\n"
            '{"task_type":"DIAGNOSIS","operations":['
            '{"operation_intent":"GET_EVIDENCE",'
            '"operation_parameters":{"command":"show ..."},'
            '"devices":[{"device_id":"<ID có trong AVAILABLE DEVICES>",'
            '"device_role":"SOURCE","access_mode":"READ"}],'
            '"dependencies":[]}]}\n\n'
            "Không đổi tên field, không dùng hostname thay cho device_id và không "
            "thêm Markdown. Operation có devices phải chứa "
            "operation_parameters.command là chuỗi không rỗng hoặc "
            "operation_parameters.commands là danh sách command không rỗng."
        )

    @staticmethod
    def _parse_plan(
        result: Any,
        default_task_type: TaskType | None = None,
    ) -> ExecutionPlanCreate:
        """Bóc JSON từ các dạng phản hồi phổ biến rồi kiểm tra bằng Pydantic."""

        try:
            content = getattr(result, "content", result)
            payload = PlannerAgent._extract_json_payload(content)
            payload = PlannerAgent._wrap_single_operation(
                payload,
                default_task_type=default_task_type,
            )
            plan = ExecutionPlanCreate.model_validate(payload)
            return PlannerAgent._normalize_write_commands(plan)
        except (ValidationError, ValueError) as exc:
            raise ValueError(
                "Planner Agent trả về JSON không đúng ExecutionPlanCreate"
            ) from exc

    @staticmethod
    def _wrap_single_operation(
        payload: dict[str, Any],
        *,
        default_task_type: TaskType | None,
    ) -> dict[str, Any]:
        """Bọc operation bị NIM bỏ lớp ngoài mà không tự tạo command hay device."""

        if "task_type" in payload or "operations" in payload:
            return payload
        operation_fields = {
            "operation_intent",
            "operation_parameters",
            "devices",
            "dependencies",
        }
        if default_task_type is None or not operation_fields.issubset(payload):
            return payload
        return {
            "task_type": default_task_type.value,
            "operations": [payload],
        }

    @staticmethod
    def _extract_json_payload(content: Any) -> dict[str, Any]:
        """Chuẩn hóa content block và bóc JSON object mà không sửa nghĩa kế hoạch."""

        if isinstance(content, dict):
            if (
                "task_type" in content
                or "operations" in content
                or "operation_intent" in content
            ):
                return content
            text = content.get("text")
            if isinstance(text, str):
                return PlannerAgent._decode_json_object(text)
            raise ValueError("Planner Agent trả object không chứa execution plan")

        if isinstance(content, list):
            text_parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            ]
            if not text_parts:
                raise ValueError("Planner Agent trả content block không có text")
            return PlannerAgent._decode_json_object("\n".join(text_parts))

        if not isinstance(content, str):
            raise ValueError("Planner Agent không trả về JSON hoặc text")
        return PlannerAgent._decode_json_object(content)

    @staticmethod
    def _decode_json_object(raw_content: str) -> dict[str, Any]:
        """Đọc JSON thuần, code fence hoặc JSON nằm sau phần dẫn nhập của model."""

        raw_content = raw_content.strip()
        candidates = [raw_content]
        candidates.extend(
            match.group(1).strip()
            for match in re.finditer(
                r"```(?:json)?\s*([\s\S]*?)```",
                raw_content,
                flags=re.IGNORECASE,
            )
        )

        decoder = json.JSONDecoder()
        for candidate in candidates:
            try:
                payload = json.loads(candidate)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                pass

            # NVIDIA NIM đôi khi thêm một câu dẫn nhập trước JSON. raw_decode từ
            # từng dấu ngoặc chỉ chấp nhận object JSON hoàn chỉnh đầu tiên.
            for match in re.finditer(r"\{", candidate):
                try:
                    payload, _ = decoder.raw_decode(candidate[match.start() :])
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    return payload

            # Chấp nhận dict literal an toàn khi model dùng dấu nháy đơn; không
            # dùng eval và không tự suy đoán hay bổ sung field nghiệp vụ.
            try:
                payload = ast.literal_eval(candidate)
            except (SyntaxError, ValueError):
                continue
            if isinstance(payload, dict):
                return payload

        raise ValueError("Không tìm thấy JSON object hoàn chỉnh trong phản hồi Planner")

    @staticmethod
    def _normalize_write_commands(plan: ExecutionPlanCreate) -> ExecutionPlanCreate:
        """Lưu đúng payload sẽ được Netmiko thực thi vào approval snapshot."""

        normalized_operations = []
        for operation in plan.operations:
            if not any(
                device.access_mode.value == "WRITE" for device in operation.devices
            ):
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
                device
                for device in operation.devices
                if device.access_mode.value == "WRITE"
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
