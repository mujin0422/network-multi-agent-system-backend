"""Planner Agent chuyển yêu cầu người dùng thành execution plan có cấu trúc."""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.planner.prompts import PLANNER_SYSTEM_PROMPT
from app.domains.execution.schemas import ExecutionPlanCreate
from app.domains.inventory.schemas import Device


class PlannerAgent:
    name = "planner-agent"
    max_validation_retries = 2

    def __init__(self, chat_model: Any) -> None:
        # Gọi model theo chế độ chat thông thường. Không dùng
        # ``with_structured_output`` vì một số NVIDIA NIM không hỗ trợ tham số
        # ``guided_json`` do LangChain tự động gửi lên endpoint.
        self._planner = chat_model

    async def plan(
        self,
        user_message: str,
        devices: list[Device],
    ) -> ExecutionPlanCreate:
        """Tạo DAG operation chỉ với những device có trong inventory."""

        inventory = [
            {
                "id": device.id,
                "hostname": device.hostname,
                "brand_id": device.brand_id,
                "category_id": device.category_id,
                "device_type": device.device_type,
                "location": device.location,
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
        for retry_number in range(self.max_validation_retries + 1):
            result = await self._planner.ainvoke(messages)
            try:
                return self._parse_plan(result)
            except ValueError as exc:
                if retry_number == self.max_validation_retries:
                    raise

                # Đưa cả kết quả sai và lỗi validation về cho model để model chỉ
                # sửa JSON, không phải lập kế hoạch lại mà thiếu ngữ cảnh.
                messages.append(
                    HumanMessage(
                        content=self._build_correction_prompt(result, exc),
                    )
                )

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
                return ExecutionPlanCreate.model_validate(content)
            if not isinstance(content, str):
                raise ValueError("Planner Agent không trả về nội dung JSON dạng text")

            raw_json = content.strip()
            if raw_json.startswith("```") and raw_json.endswith("```"):
                lines = raw_json.splitlines()
                raw_json = "\n".join(lines[1:-1]).strip()

            return ExecutionPlanCreate.model_validate_json(raw_json)
        except (ValidationError, ValueError) as exc:
            raise ValueError(
                "Planner Agent trả về JSON không đúng ExecutionPlanCreate"
            ) from exc
