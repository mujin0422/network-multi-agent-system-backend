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

        # Bước 1: Chuẩn hóa ngữ cảnh topology và interface được cung cấp.
        node_interfaces = node_interfaces or {}
        topology_neighbors = topology_neighbors or {}

        # Bước 2: Chuyển inventory thành dữ liệu công khai, không chứa credential.
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

        # Bước 3: Tạo prompt gồm yêu cầu, inventory, topology, playbook và schema.
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
            # Bước 4: Gọi LLM trong giới hạn timeout và số lần validation retry.
            async with asyncio.timeout(self.timeout_seconds):
                for retry_number in range(self.max_validation_retries + 1):
                    result = await self._planner.ainvoke(messages)
                    try:
                        # Bước 5: Bóc JSON và kiểm tra kế hoạch bằng schema nghiệp vụ.
                        plan = self._parse_plan(
                            result,
                            default_task_type=(
                                TaskType.DIAGNOSIS if diagnostic_playbooks else None
                            ),
                        )
                        self._validate_requested_access(user_message, plan)
                        return plan
                    except ValueError as exc:
                        if retry_number == self.max_validation_retries:
                            raise

                        # Bước 6: Gửi lỗi validation cho LLM sửa mà không mất ngữ cảnh.
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
            "thêm Markdown. Operation READ phải có command; Operation WRITE "
            "phải có operation_parameters.configuration_requirements là object."
        )

    @staticmethod
    def _validate_requested_access(
        user_message: str,
        plan: ExecutionPlanCreate,
    ) -> None:
        """Không cho Planner làm mất WRITE intent được người dùng yêu cầu rõ."""

        normalized_message = user_message.casefold()
        write_patterns = (
            r"\bthực hiện\s+(?:việc\s+)?cấu hình\b",
            r"\bhãy\s+cấu hình\b",
            r"\bcấu hình\s+cho\b",
            r"\bkhắc phục\b",
            r"\bsửa\s+(?:lỗi|cấu hình)\b",
            r"\b(?:bật|tắt)\s+(?:cổng|interface|ospf|mpls|ldp|bgp)\b",
        )
        requests_write = any(
            re.search(pattern, normalized_message) for pattern in write_patterns
        )
        if not requests_write:
            return

        has_write = any(
            device.access_mode.value == "WRITE"
            for operation in plan.operations
            for device in operation.devices
        )
        if not has_write:
            raise ValueError(
                "Người dùng yêu cầu thực hiện thay đổi nhưng kế hoạch không có "
                "Operation WRITE. Hãy giữ các bước READ cần thiết và bổ sung WRITE "
                "với configuration_requirements cùng dependency phù hợp."
            )

    @staticmethod
    def _parse_plan(
        result: Any,
        default_task_type: TaskType | None = None,
    ) -> ExecutionPlanCreate:
        """Bóc JSON từ các dạng phản hồi phổ biến rồi kiểm tra bằng Pydantic."""

        try:
            # Bước 1: Lấy content từ phản hồi của model.
            content = getattr(result, "content", result)
            # Bước 2: Bóc JSON từ text hoặc content block.
            payload = PlannerAgent._extract_json_payload(content)
            # Bước 3: Khôi phục lớp plan khi model chỉ trả một operation hợp lệ.
            payload = PlannerAgent._wrap_single_operation(
                payload,
                default_task_type=default_task_type,
            )
            # Bước 4: Xác thực payload bằng ExecutionPlanCreate.
            return ExecutionPlanCreate.model_validate(payload)
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
        # Bước 1: Thu thập JSON thuần và các JSON code fence có thể có.
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
            # Bước 2: Ưu tiên giải mã toàn bộ candidate như JSON chuẩn.
            try:
                payload = json.loads(candidate)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError:
                pass

            # Bước 3: Tìm object đầu tiên nếu model thêm câu dẫn trước JSON.
            for match in re.finditer(r"\{", candidate):
                try:
                    payload, _ = decoder.raw_decode(candidate[match.start() :])
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    return payload

            # Bước 4: Đọc an toàn dict literal khi model dùng dấu nháy đơn.
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
        # Bước 1: Duyệt từng operation và giữ nguyên các operation READ.
        for operation in plan.operations:
            if not any(
                device.access_mode.value == "WRITE" for device in operation.devices
            ):
                normalized_operations.append(operation)
                continue

            parameters = dict(operation.operation_parameters)
            # Bước 2: Quy đổi command đơn hoặc commands thành một danh sách.
            raw_commands = parameters.pop("commands", parameters.pop("command", None))
            commands = [raw_commands] if isinstance(raw_commands, str) else raw_commands
            if not isinstance(commands, list):
                raise ValueError("Operation WRITE không chứa danh sách command hợp lệ")
            # Bước 3: Loại lệnh quản lý phiên trước khi tạo approval snapshot.
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
        # Bước 1: Chỉ kiểm tra những operation có quyền WRITE.
        for operation in plan.operations:
            write_devices = [
                device
                for device in operation.devices
                if device.access_mode.value == "WRITE"
            ]
            if not write_devices:
                continue
            commands = operation.operation_parameters.get("commands", [])
            # Bước 2: Tìm các command khai báo interface vật lý.
            for command in commands:
                match = physical_interface.fullmatch(command.strip())
                if match is None:
                    continue
                interface_name = match.group(1).split(".", maxsplit=1)[0]
                # Bước 3: Đối chiếu interface với inventory của từng thiết bị.
                for device in write_devices:
                    available = interfaces_by_device_id.get(device.device_id, [])
                    if available and interface_name not in available:
                        raise ValueError(
                            f"Interface '{interface_name}' không tồn tại trên "
                            f"device '{device.device_id}'. Interface hợp lệ: "
                            f"{', '.join(available)}"
                        )
