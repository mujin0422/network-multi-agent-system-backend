"""Analyst Agent phân tích output, không kết nối thiết bị."""

import asyncio
import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from app.agents.analyst.prompts import ANALYST_SYSTEM_PROMPT
from app.agents.analyst.schemas import AnalysisResult, ConfigurationProposalSet


class AnalystAgent:

    name = "analyst-agent"


    def __init__(
        self,
        chat_model: Any,
        max_validation_retries: int = 2,
        timeout_seconds: float = 120.0,
    ) -> None:
        """Khởi tạo Analyst Agent với model chat, số lần retry và timeout."""
        self._analyst = chat_model
        self.max_validation_retries = max_validation_retries
        self.timeout_seconds = timeout_seconds


    async def analyze(self, execution_outputs: list[dict[str, Any]]) -> AnalysisResult:
        """Phân tích output trong thời hạn cấu hình cho toàn bộ các lần retry."""
        try:
            # Bước 1: Chạy toàn bộ luồng phân tích trong giới hạn timeout.
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

        # Bước 1: Chuẩn bị schema đầu ra dành riêng cho phản hồi của LLM.
        response_schema = AnalysisResult.model_json_schema()
        # suspected_causes là kết quả của backend Causal Evidence Gate, không
        # cho LLM tự đưa nguyên nhân vào nhánh không được evaluator chấm.
        response_schema.get("properties", {}).pop("suspected_causes", None)
        # CLI preview dùng một lần gọi schema nhỏ riêng để lỗi JSON phân tích RCA
        # không làm mất phần cấu hình người dùng đã yêu cầu.
        response_schema.get("properties", {}).pop("configuration_proposals", None)
        prompt = (
            "EXECUTION OUTPUTS:\n"
            f"{json.dumps(execution_outputs, ensure_ascii=False)}\n\n"
            "RESPONSE JSON SCHEMA:\n"
            f"{json.dumps(response_schema, ensure_ascii=False)}\n\n"
            "Chỉ trả về một JSON object hợp lệ, không dùng Markdown."
        )
        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        # Bước 2: Gọi LLM và thử lại khi structured output không hợp lệ.
        for retry_number in range(self.max_validation_retries + 1):
            result = await self._analyst.ainvoke(messages)
            try:
                # Bước 3: Bóc JSON và xác thực AnalysisResult.
                return self._parse_result(result)
            except ValueError as exc:
                if retry_number == self.max_validation_retries:
                    raise
                # Bước 4: Gửi lỗi và giới hạn độ dài để model tạo lại JSON.
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
                            "root_causes, configuration_proposals và luôn đặt mọi "
                            "key trong dấu ngoặc kép. Escape dấu ngoặc kép bên trong "
                            "chuỗi và không đặt dấu phẩy sau phần tử cuối.\n"
                            f"Phần đầu nội dung sai để đối chiếu: {invalid_content[:600]}"
                        )
                    )
                )
        raise RuntimeError("Analyst Agent không thể tạo kết quả phân tích")

    async def propose_configurations(
        self,
        user_request: str,
        execution_outputs: list[dict[str, Any]],
    ) -> ConfigurationProposalSet:
        """Sinh CLI preview theo thiết bị mà không thực thi hoặc tạo approval."""

        schema = ConfigurationProposalSet.model_json_schema()
        messages = [
            SystemMessage(
                content=(
                    "Bạn tạo cấu hình mạng CHỈ ĐỂ ĐỀ XUẤT, tuyệt đối không tuyên bố "
                    "đã thực thi. Dựa trên USER REQUEST và output READ thực tế. "
                    "Giữ nguyên hostname, interface, IP và CLI. Không đoán tham số "
                    "quan trọng khi dữ liệu chưa đủ; khi đó trả configurations=[]. "
                    "Mỗi thiết bị có device, commands theo đúng thứ tự và rationale."
                )
            ),
            HumanMessage(
                content=(
                    f"USER REQUEST:\n{user_request}\n\n"
                    "READ EXECUTION OUTPUTS:\n"
                    f"{json.dumps(execution_outputs, ensure_ascii=False)}\n\n"
                    "RESPONSE JSON SCHEMA:\n"
                    f"{json.dumps(schema, ensure_ascii=False)}\n\n"
                    "Chỉ trả JSON object hợp lệ, không dùng Markdown."
                )
            ),
        ]
        async with asyncio.timeout(self.timeout_seconds):
            for retry_number in range(self.max_validation_retries + 1):
                result = await self._analyst.ainvoke(messages)
                try:
                    content = getattr(result, "content", result)
                    if not content:
                        content = getattr(result, "additional_kwargs", {}).get(
                            "reasoning_content", ""
                        )
                    if isinstance(content, dict):
                        return ConfigurationProposalSet.model_validate(content)
                    raw_json = self._extract_json_object(str(content))
                    return ConfigurationProposalSet.model_validate_json(raw_json)
                except (ValidationError, ValueError) as exc:
                    if retry_number == self.max_validation_retries:
                        raise ValueError(
                            "Analyst Agent không thể tạo CLI đề xuất có cấu trúc"
                        ) from exc
                    messages.append(
                        HumanMessage(
                            content=(
                                f"JSON CLI đề xuất chưa hợp lệ: {exc}. "
                                "Hãy trả lại một JSON object ngắn, đầy đủ đúng schema."
                            )
                        )
                    )
        raise RuntimeError("Analyst Agent không thể tạo CLI đề xuất")

    @staticmethod
    def _parse_result(result: Any) -> AnalysisResult:
        """Bóc JSON object từ phản hồi của Analyst Agent và xác thực bằng AnalysisResult."""
        try:
            # Bước 1: Ưu tiên content chính, chỉ dùng reasoning khi content rỗng.
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

            # Bước 2: Bóc JSON object từ phản hồi dạng text.
            raw_json = AnalystAgent._extract_json_object(content)
            try:
                # Bước 3: Xác thực JSON chuẩn trước khi áp dụng sửa lỗi giới hạn.
                return AnalystAgent._validate_submission(json.loads(raw_json))
            except (ValidationError, ValueError):
                # Một số model local/NIM đôi khi bỏ dấu ngoặc kép ở key hoặc
                # thêm dấu phẩy cuối dù prompt đã yêu cầu JSON nghiêm ngặt.
                # Chỉ sửa các key thuộc schema để không thay đổi nội dung lệnh.
                # Bước 4: Chỉ sửa key thuộc schema và dấu phẩy cuối.
                repaired_json = re.sub(
                    r'([{,]\s*)(summary|findings|likely_causes|recommendations|requires_more_data|confidence|evidence_gaps|suggested_checks|commands|reason|is_anomaly|root_causes|suspected_causes|configuration_proposals|rationale|device|interface|fault_type)(\s*:)',
                    r'\1"\2"\3',
                    raw_json,
                )
                repaired_json = re.sub(r",(\s*[}\]])", r"\1", repaired_json)
                return AnalystAgent._validate_submission(json.loads(repaired_json))
        except (ValidationError, ValueError) as exc:
            raise ValueError("Analyst Agent trả JSON không đúng AnalysisResult") from exc

    @staticmethod
    def _validate_submission(payload: Any) -> AnalysisResult:
        """Xác thực payload của Analyst Agent bằng AnalysisResult."""

        # Bước 1: Bảo đảm submission là một JSON object.
        if not isinstance(payload, dict):
            raise ValueError("Analyst submission must be a JSON object")
        payload = {key: value for key, value in payload.items() if key != "suspected_causes"}
        # Bước 2: Yêu cầu Agent khai báo rõ các trường RCA và evidence.
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
        # Bước 3: Xác thực toàn bộ payload bằng AnalysisResult.
        return AnalysisResult.model_validate(payload)

    @staticmethod
    def _extract_json_object(content: str) -> str:
        # Bước 1: Loại code fence bao quanh nếu model sử dụng Markdown.
        raw_json = content.strip()
        if raw_json.startswith("```") and raw_json.endswith("```"):
            raw_json = "\n".join(raw_json.splitlines()[1:-1]).strip()
        # Bước 2: Lấy JSON object ngoài cùng từ nội dung còn lại.
        object_start = raw_json.find("{")
        object_end = raw_json.rfind("}")
        if object_start >= 0 and object_end > object_start:
            return raw_json[object_start : object_end + 1]
        return raw_json
