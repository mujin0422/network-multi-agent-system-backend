"""Structured output của Analyst Agent."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.evaluation.schemas.diagnosis import PredictedRootCause


AnalysisItem = Annotated[str, Field(min_length=1, max_length=240)]


class DiagnosticCheck(BaseModel):
    """Một phép kiểm tra READ-only được đề nghị cho vòng điều tra tiếp theo."""

    model_config = ConfigDict(str_strip_whitespace=True)

    device: str = Field(min_length=1, max_length=100)
    commands: list[str] = Field(min_length=1, max_length=4)
    reason: str = Field(min_length=1, max_length=240)

    @field_validator("commands")
    @classmethod
    def validate_read_commands(cls, commands: list[str]) -> list[str]:
        """Chỉ cho phép lệnh quan sát, tuyệt đối không sinh thay đổi cấu hình."""

        allowed = ("show ", "ping ", "traceroute ")
        normalized = [command.strip() for command in commands if command.strip()]
        if not normalized or any(
            not command.lower().startswith(allowed) for command in normalized
        ):
            raise ValueError("Diagnostic check chỉ chấp nhận show/ping/traceroute")
        return normalized

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
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_gaps: list[AnalysisItem] = Field(default_factory=list, max_length=4)
    suggested_checks: list[DiagnosticCheck] = Field(default_factory=list, max_length=4)
    # The same diagnosis report also produces the machine-readable submission.
    # Defaults preserve older non-benchmark Agent callers.
    is_anomaly: bool | None = None
    root_causes: list[PredictedRootCause] = Field(default_factory=list, max_length=8)

