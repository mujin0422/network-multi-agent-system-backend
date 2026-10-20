"""Analyst Agent phân tích output, không kết nối thiết bị."""

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.analyst.prompts import ANALYST_SYSTEM_PROMPT
from app.agents.analyst.schemas import AnalysisResult


class AnalystAgent:
    name = "analyst-agent"

    def __init__(self, chat_model: Any) -> None:
        self._analyst = chat_model.with_structured_output(AnalysisResult)

    # Phân tích output từ execution agent, trả về kết quả phân tích có cấu trúc.
    async def analyze(self, execution_outputs: list[dict[str, Any]]) -> AnalysisResult:
        result = await self._analyst.ainvoke(
            [
                SystemMessage(content=ANALYST_SYSTEM_PROMPT),
                HumanMessage(
                    content=json.dumps(execution_outputs, ensure_ascii=False)
                ),
            ]
        )
        return AnalysisResult.model_validate(result)
