"""Structured output của Analyst Agent."""

from pydantic import BaseModel, Field


# Kết quả phân tích của Analyst Agent, bao gồm tóm tắt, phát hiện, nguyên nhân có khả năng, khuyến nghị và yêu cầu thêm dữ liệu nếu cần.
class AnalysisResult(BaseModel):
    summary: str = Field(
        max_length=1200,
        description="Tóm tắt kết quả bằng tiếng Việt, tối đa 1200 ký tự.",
    )
    findings: list[str] = Field(default_factory=list, max_length=5)
    likely_causes: list[str] = Field(default_factory=list, max_length=5)
    recommendations: list[str] = Field(default_factory=list, max_length=5)
    requires_more_data: bool = False
