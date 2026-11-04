"""Analyst Agent phân tích output, không kết nối thiết bị."""

import asyncio
import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.analyst.prompts import ANALYST_SYSTEM_PROMPT
from app.agents.analyst.schemas import AnalysisResult


class AnalystAgent:
    name = "analyst-agent"

    def __init__(
        self,
        chat_model: Any,
        max_validation_retries: int = 2,
        timeout_seconds: float = 120.0,
    ) -> None:
        # Dùng JSON thường vì NVIDIA NIM có model không hỗ trợ guided_json.
        self._analyst = chat_model
        self.max_validation_retries = max_validation_retries
        self.timeout_seconds = timeout_seconds

    # Phân tích output từ execution agent, trả về kết quả phân tích có cấu trúc.
    async def analyze(self, execution_outputs: list[dict[str, Any]]) -> AnalysisResult:
        """Phân tích output trong thời hạn cấu hình cho toàn bộ các lần retry."""

        try:
            return await asyncio.wait_for(
                self._analyze_with_retries(execution_outputs),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            raise TimeoutError(
                f"Analyst Agent không phản hồi trong {self.timeout_seconds:g} giây"
            ) from exc

    async def _analyze_with_retries(
        self,
        execution_outputs: list[dict[str, Any]],
    ) -> AnalysisResult:
        """Gọi model và yêu cầu sửa structured output theo số retry cấu hình."""

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
                            "Giới hạn: summary <= 600 ký tự; mỗi danh sách <= 4 ý; "
                            "mỗi ý <= 240 ký tự. Không lặp dữ kiện giữa các phần.\n"
                            "Dùng đủ các key summary, findings, likely_causes, "
                            "recommendations, requires_more_data, confidence, "
                            "evidence_gaps, suggested_checks, is_anomaly, "
                            "root_causes và luôn đặt mọi "
                            "key trong dấu ngoặc kép. Escape dấu ngoặc kép bên trong "
                            "chuỗi và không đặt dấu phẩy sau phần tử cuối.\n"
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
                return AnalystAgent._validate_submission(content)
            if not isinstance(content, str):
                raise ValueError("Analyst Agent không trả JSON dạng text")
            raw_json = AnalystAgent._extract_json_object(content)
            try:
                return AnalystAgent._validate_submission(json.loads(raw_json))
            except (ValidationError, ValueError):
                # Một số model local/NIM đôi khi bỏ dấu ngoặc kép ở key hoặc
                # thêm dấu phẩy cuối dù prompt đã yêu cầu JSON nghiêm ngặt.
                # Chỉ sửa các key thuộc schema để không thay đổi nội dung lệnh.
                repaired_json = re.sub(
                    r'([{,]\s*)(summary|findings|likely_causes|recommendations|requires_more_data|confidence|evidence_gaps|suggested_checks|commands|reason|is_anomaly|root_causes|device|interface|fault_type)(\s*:)',
                    r'\1"\2"\3',
                    raw_json,
                )
                repaired_json = re.sub(r",(\s*[}\]])", r"\1", repaired_json)
                return AnalystAgent._validate_submission(json.loads(repaired_json))
        except (ValidationError, ValueError) as exc:
            raise ValueError("Analyst Agent trả JSON không đúng AnalysisResult") from exc

    @staticmethod
    def _validate_submission(payload: Any) -> AnalysisResult:
        """Require explicit Agent-provided RCA fields, never silently default [].

        The Pydantic defaults remain for older non-LLM callers and safe fallbacks.
        """
        if not isinstance(payload, dict):
            raise ValueError("Analyst submission must be a JSON object")
        required = {
            "is_anomaly",
            "root_causes",
            "confidence",
            "evidence_gaps",
            "suggested_checks",
        }
        if not required.issubset(payload):
            raise ValueError(
                "Analyst must explicitly submit diagnosis confidence and evidence gaps"
            )
        return AnalysisResult.model_validate(payload)

    @staticmethod
    def _extract_json_object(content: str) -> str:
        raw_json = content.strip()
        if raw_json.startswith("```") and raw_json.endswith("```"):
            raw_json = "\n".join(raw_json.splitlines()[1:-1]).strip()
        object_start = raw_json.find("{")
        object_end = raw_json.rfind("}")
        if object_start >= 0 and object_end > object_start:
            return raw_json[object_start : object_end + 1]
        return raw_json
