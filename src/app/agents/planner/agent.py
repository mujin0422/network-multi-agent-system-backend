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
from app.domains.conversation.schemas import Message
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
        conversation_history: list[Message] | None = None,
    ) -> ExecutionPlanCreate:
        """Tạo DAG operation chỉ với những device có trong inventory."""

        # Bước 1: Chuẩn hóa ngữ cảnh topology và interface được cung cấp.
        node_interfaces = node_interfaces or {}
        topology_neighbors = topology_neighbors or {}
        conversation_history = conversation_history or []

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
        recent_context = [
            {
                "sender": item.sender_by.value,
                "message_type": item.message_type.value,
                "content": item.message,
            }
            for item in conversation_history
        ]

        # Bước 3: Tạo prompt gồm yêu cầu, inventory, topology, playbook và schema.
        prompt = (
            "RECENT CONVERSATION CONTEXT "
            "(oldest to newest; use only to resolve references in the current request):\n"
            f"{json.dumps(recent_context, ensure_ascii=False)}\n\n"
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
        missing_write = "không có Operation WRITE" in str(validation_error)
        forbidden_write = (
            "chỉ đọc/thu thập dữ liệu" in str(validation_error)
            or "chỉ đề xuất cấu hình" in str(validation_error)
        )
        if missing_write:
            required_structure = (
                "KẾ HOẠCH BẮT BUỘC PHẢI GIỮ CÁC BƯỚC READ VÀ BỔ SUNG WRITE:\n"
                '{"task_type":"CONFIGURATION","operations":['
                '{"operation_intent":"GET_CURRENT_STATE",'
                '"operation_parameters":{"command":"show ..."},'
                '"devices":[{"device_id":"<ID thiết bị nguồn>",'
                '"device_role":"SOURCE","access_mode":"READ"}],'
                '"dependencies":[]},'
                '{"operation_intent":"CONFIGURE_TARGET",'
                '"operation_parameters":{"configuration_requirements":'
                '{"goal":"<trạng thái cấu hình người dùng yêu cầu>",'
                '"derive_from_previous_operations":true}},'
                '"devices":[{"device_id":"<ID thiết bị đích>",'
                '"device_role":"TARGET","access_mode":"WRITE"}],'
                '"dependencies":[{"depends_on_order":1,"condition":"ON_SUCCESS"}]},'
                '{"operation_intent":"VERIFY_TARGET",'
                '"operation_parameters":{"command":"show ..."},'
                '"devices":[{"device_id":"<ID thiết bị đích>",'
                '"device_role":"TARGET","access_mode":"READ"}],'
                '"dependencies":[{"depends_on_order":2,"condition":"ON_SUCCESS"}]}]}'
                "\nKhông được loại bỏ WRITE chỉ vì tham số cấu hình phải "
                "suy ra từ kết quả READ. Trong trường hợp đó, hãy mô tả mục tiêu "
                "và nguồn dữ liệu trong configuration_requirements; Configuration "
                "Agent sẽ tạo CLI sau khi các dependency READ hoàn tất."
            )
        elif forbidden_write:
            required_structure = (
                "KẾ HOẠCH BẮT BUỘC CHỈ ĐƯỢC CÓ READ:\n"
                '{"task_type":"INFORMATION_RETRIEVAL","operations":['
                '{"operation_intent":"GET_CURRENT_STATE",'
                '"operation_parameters":{"command":"show ..."},'
                '"devices":[{"device_id":"<ID có trong AVAILABLE DEVICES>",'
                '"device_role":"SOURCE","access_mode":"READ"}],'
                '"dependencies":[]}]}'
                "\nLoại bỏ toàn bộ Operation WRITE. Nếu người dùng chỉ yêu cầu "
                "đề xuất, hệ thống sẽ tạo CLI preview trong phản hồi sau khi "
                "phân tích dữ liệu READ; không tạo yêu cầu phê duyệt."
            )
        else:
            required_structure = (
                "CẤU TRÚC TỐI THIỂU BẮT BUỘC:\n"
                '{"task_type":"DIAGNOSIS","operations":['
                '{"operation_intent":"GET_EVIDENCE",'
                '"operation_parameters":{"command":"show ..."},'
                '"devices":[{"device_id":"<ID có trong AVAILABLE DEVICES>",'
                '"device_role":"SOURCE","access_mode":"READ"}],'
                '"dependencies":[]}]}'
            )
        return (
            "JSON trước đó không hợp lệ. Hãy sửa và chỉ trả về JSON object hoàn chỉnh.\n\n"
            f"VALIDATION ERROR:\n{validation_error}\n\n"
            f"INVALID JSON:\n{invalid_content}\n\n"
            f"{required_structure}\n\n"
            "Không đổi tên field, không dùng hostname thay cho device_id và không "
            "thêm Markdown. Operation READ phải có command; Operation WRITE "
            "phải có operation_parameters.configuration_requirements là object. "
            "Không tạo Operation ANALYZE/SUMMARIZE/INTERPRET/CORRELATE; "
            "Analyst Agent sẽ thực hiện phần phân tích sau execution."
        )

    @staticmethod
    def _validate_requested_access(
        user_message: str,
        plan: ExecutionPlanCreate,
    ) -> None:
        """Giữ nguyên READ-only hoặc WRITE intent được yêu cầu rõ."""

        normalized_message = user_message.casefold()
        has_write = any(
            device.access_mode.value == "WRITE"
            for operation in plan.operations
            for device in operation.devices
        )
        read_only_patterns = (
            r"chỉ\s+(?:được\s+)?(?:thu thập|kiểm tra|chẩn đoán|phân tích)\s+dữ liệu",
            r"\bkhông\s+(?:được\s+)?(?:khắc phục|cấu hình|thay đổi|sửa)\b",
            r"\b(?:xem|lấy|kiểm\s+tra|hiển\s+thị)\s+cấu\s+hình\b",
            r"\bread[ -]?only\b",
        )
        requests_read_only = any(
            re.search(pattern, normalized_message) for pattern in read_only_patterns
        )
        proposal_only = PlannerAgent.is_configuration_proposal(user_message)
        if requests_read_only or proposal_only:
            if has_write:
                raise ValueError(
                    "Người dùng yêu cầu chỉ đọc/thu thập dữ liệu hoặc chỉ đề xuất cấu hình nhưng "
                    "kế hoạch có Operation WRITE. Hãy loại bỏ toàn bộ WRITE "
                    "và chỉ giữ Operation READ để thu thập dữ liệu; CLI đề xuất "
                    "sẽ được trả trong phản hồi và không được thực thi."
                )
            return

        write_patterns = (
            r"\bthực hiện\s+(?:việc\s+)?cấu hình\b",
            r"\bhãy\s+cấu hình\b",
            r"\bcấu hình\s+cho\b",
            r"\bkhắc phục\b",
            r"\bsửa\s+(?:lỗi|cấu hình)\b",
            r"\b(?:bật|tắt)\s+(?:cổng|interface|ospf|mpls|ldp|bgp)\b",
            r"\bcấu\s+hình\b",
        )
        requests_write = any(
            re.search(pattern, normalized_message) for pattern in write_patterns
        )
        if not requests_write:
            return

        if not has_write:
            raise ValueError(
                "Người dùng yêu cầu thực hiện thay đổi nhưng kế hoạch không có "
                "Operation WRITE. Hãy giữ các bước READ cần thiết và bổ sung WRITE "
                "với configuration_requirements cùng dependency phù hợp."
            )

    @staticmethod
    def is_configuration_proposal(user_message: str) -> bool:
        """Nhận diện yêu cầu chỉ xem CLI, không đồng nhất mục đích với thực thi."""

        normalized_message = user_message.casefold()
        proposal_patterns = (
            r"\bđề\s+xuất\b",
            r"\bkhuyến\s+nghị\b",
            r"\bcho\s+(?:tôi\s+)?(?:các\s+)?lệnh\b",
            r"\bliệt\s+kê\s+(?:các\s+)?lệnh\b",
            r"\bnên\s+cấu\s+hình\s+(?:như\s+)?thế\s+nào\b",
        )
        explicit_execution_patterns = (
            r"\bthực\s+hiện\s+(?:việc\s+)?(?:các?\s+)?(?:cấu\s+hình|thay\s+đổi|lệnh)\b",
            r"\bthực\s+thi\s+(?:các?\s+)?(?:cấu\s+hình|lệnh)\b",
            r"\báp\s+dụng\s+(?:các?\s+)?(?:cấu\s+hình|thay\s+đổi|lệnh)\b",
            r"\btriển\s+khai\s+(?:các?\s+)?(?:cấu\s+hình|thay\s+đổi)\b",
            r"\bhãy\s+cấu\s+hình\b",
            r"\btiến\s+hành\s+cấu\s+hình\b",
        )
        return any(
            re.search(pattern, normalized_message) for pattern in proposal_patterns
        ) and not any(
            re.search(pattern, normalized_message)
            for pattern in explicit_execution_patterns
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
            # Bước 4: Loại bước phân tích thuần túy khỏi execution DAG.
            payload = PlannerAgent._remove_non_executable_operations(payload)
            # Bước 5: Xác thực payload bằng ExecutionPlanCreate.
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
        if not operation_fields.issubset(payload):
            return payload
        return {
            "task_type": (default_task_type or TaskType.UNCLASSIFIED).value,
            "operations": [payload],
        }

    @staticmethod
    def _remove_non_executable_operations(
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Loại bước phân tích thuần túy và nối lại dependency của DAG.

        Analyst Agent chịu trách nhiệm phân tích kết quả sau khi Network Agent
        hoàn tất. Nếu giữ các bước này trong execution plan, chúng không có
        device mapping, bị đánh dấu SKIPPED và làm sai trạng thái Task thành
        PARTIAL_SUCCESS dù mọi lệnh mạng đều thành công.
        """

        operations = payload.get("operations")
        if not isinstance(operations, list):
            return payload

        non_executable_prefixes = (
            "ANALYZE",
            "SUMMARIZE",
            "INTERPRET",
            "CORRELATE",
        )

        def is_non_executable(item: Any) -> bool:
            if not isinstance(item, dict):
                return False
            intent = str(item.get("operation_intent", "")).upper()
            parameters = item.get("operation_parameters")
            parameters = parameters if isinstance(parameters, dict) else {}
            has_command = bool(parameters.get("command") or parameters.get("commands"))
            has_requirements = bool(parameters.get("configuration_requirements"))
            return (
                intent.startswith(non_executable_prefixes)
                and not has_command
                and not has_requirements
            )

        removed_orders = {
            order
            for order, operation in enumerate(operations, start=1)
            if is_non_executable(operation)
        }
        if not removed_orders:
            return payload

        kept_orders = [
            order
            for order in range(1, len(operations) + 1)
            if order not in removed_orders
        ]
        new_order_by_old = {
            old_order: new_order
            for new_order, old_order in enumerate(kept_orders, start=1)
        }

        def resolve_dependency(old_order: int) -> list[int]:
            """Truy ngược qua bước bị loại để giữ dependency thực thi gần nhất."""

            if old_order in new_order_by_old:
                return [new_order_by_old[old_order]]
            if old_order < 1 or old_order > len(operations):
                return []
            removed = operations[old_order - 1]
            if not isinstance(removed, dict):
                return []
            resolved: list[int] = []
            for dependency in removed.get("dependencies", []):
                if not isinstance(dependency, dict):
                    continue
                dependency_order = dependency.get("depends_on_order")
                if isinstance(dependency_order, int):
                    resolved.extend(resolve_dependency(dependency_order))
            return resolved

        normalized_operations: list[Any] = []
        for old_order in kept_orders:
            item = operations[old_order - 1]
            if not isinstance(item, dict):
                normalized_operations.append(item)
                continue
            dependencies: list[Any] = []
            seen_orders: set[int] = set()
            for dependency in item.get("dependencies", []):
                if not isinstance(dependency, dict):
                    dependencies.append(dependency)
                    continue
                dependency_order = dependency.get("depends_on_order")
                if not isinstance(dependency_order, int):
                    dependencies.append(dependency)
                    continue
                for resolved_order in resolve_dependency(dependency_order):
                    if resolved_order in seen_orders:
                        continue
                    seen_orders.add(resolved_order)
                    dependencies.append(
                        {**dependency, "depends_on_order": resolved_order}
                    )
            normalized_operations.append({**item, "dependencies": dependencies})

        return {**payload, "operations": normalized_operations}

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
