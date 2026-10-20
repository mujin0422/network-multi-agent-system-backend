"""Structured output của Analyst Agent."""

from pydantic import BaseModel, Field


# Kết quả phân tích của Analyst Agent, bao gồm tóm tắt, phát hiện, nguyên nhân có khả năng, khuyến nghị và yêu cầu thêm dữ liệu nếu cần.
class AnalysisResult(BaseModel):
    summary: str = Field(description="Tóm tắt kết quả bằng tiếng Việt.")
    findings: list[str] = Field(default_factory=list)
    likely_causes: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    requires_more_data: bool = False
