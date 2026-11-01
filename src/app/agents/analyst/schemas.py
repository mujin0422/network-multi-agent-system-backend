"""Structured output của Analyst Agent."""

from typing import Annotated

from pydantic import BaseModel, Field


AnalysisItem = Annotated[str, Field(min_length=1, max_length=240)]


# Kết quả phân tích của Analyst Agent, bao gồm tóm tắt, phát hiện, nguyên nhân có khả năng, khuyến nghị và yêu cầu thêm dữ liệu nếu cần.
class AnalysisResult(BaseModel):
    summary: str = Field(
        max_length=600,
        description="Kết luận tổng thể bằng tiếng Việt, tối đa 600 ký tự.",
    )
    findings: list[AnalysisItem] = Field(default_factory=list, max_length=4)
    likely_causes: list[AnalysisItem] = Field(default_factory=list, max_length=4)
    recommendations: list[AnalysisItem] = Field(default_factory=list, max_length=4)
    requires_more_data: bool = False
