"""Analyst Agent phân tích output, không kết nối thiết bị."""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.analyst.prompts import ANALYST_SYSTEM_PROMPT
from app.agents.analyst.schemas import AnalysisResult


class AnalystAgent:
    name = "analyst-agent"
    max_validation_retries = 2

    def __init__(self, chat_model: Any) -> None:
        # Dùng JSON thường vì NVIDIA NIM có model không hỗ trợ guided_json.
        self._analyst = chat_model

    # Phân tích output từ execution agent, trả về kết quả phân tích có cấu trúc.
    async def analyze(self, execution_outputs: list[dict[str, Any]]) -> AnalysisResult:
        prompt = (
            "EXECUTION OUTPUTS:\n"
            f"{json.dumps(execution_outputs, ensure_ascii=False)}\n\n"
            "RESPONSE JSON SCHEMA:\n"
            f"{json.dumps(AnalysisResult.model_json_schema(), ensure_ascii=False)}\n\n"
            "Chỉ trả về một JSON object hợp lệ, không dùng Markdown."
        )
        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        for retry_number in range(self.max_validation_retries + 1):
            result = await self._analyst.ainvoke(messages)
            try:
                return self._parse_result(result)
            except ValueError as exc:
                if retry_number == self.max_validation_retries:
                    raise
                invalid_content = str(getattr(result, "content", result))
                messages.append(
                    HumanMessage(
                        content=(
                            "Kết quả trước không hợp lệ hoặc đã bị cắt. Hãy tạo lại "
                            "một JSON MỚI, ngắn gọn và hoàn chỉnh; không tiếp tục đoạn cũ.\n"
                            f"Lỗi: {exc.__cause__ or exc}\n"
                            "Giới hạn: summary <= 1200 ký tự; mỗi danh sách <= 5 ý; "
                            "mỗi ý <= 300 ký tự.\n"
                            f"Phần đầu nội dung sai để đối chiếu: {invalid_content[:600]}"
                        )
                    )
                )
        raise RuntimeError("Analyst Agent không thể tạo kết quả phân tích")

    @staticmethod
    def _parse_result(result: Any) -> AnalysisResult:
        try:
            content = getattr(result, "content", result)
            # Một số NVIDIA model vẫn trả JSON trong reasoning_content dù đã
            # yêu cầu tắt thinking. Chỉ dùng giá trị này khi content thật sự rỗng.
            if not content:
                additional_kwargs = getattr(result, "additional_kwargs", {})
                content = additional_kwargs.get("reasoning_content", "")
            if isinstance(content, dict):
                return AnalysisResult.model_validate(content)
            if not isinstance(content, str):
                raise ValueError("Analyst Agent không trả JSON dạng text")
            raw_json = content.strip()
            if raw_json.startswith("```") and raw_json.endswith("```"):
                raw_json = "\n".join(raw_json.splitlines()[1:-1]).strip()
            return AnalysisResult.model_validate_json(raw_json)
        except (ValidationError, ValueError) as exc:
            raise ValueError("Analyst Agent trả JSON không đúng AnalysisResult") from exc
