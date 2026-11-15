"""Structured output của Analyst Agent."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domains.evaluation.schemas.diagnosis import PredictedRootCause


AnalysisItem = Annotated[str, Field(min_length=1, max_length=240)]


class DiagnosticCheck(BaseModel):
    """Đề xuất một phép kiểm tra (READ-only) chỉ đọc để thu thập thêm bằng chứng chẩn đoán."""
    model_config = ConfigDict(str_strip_whitespace=True)

    device: str = Field(min_length=1, max_length=100, description="Tên thiết bị hoặc địa chỉ IP của thiết bị cần kiểm tra.")
    commands: list[str] = Field(min_length=1, max_length=4, description="Danh sách lệnh cần thực hiện.")
    reason: str = Field(min_length=1, max_length=240, description="Lý do thực hiện phép kiểm tra.")

    @field_validator("commands")
    @classmethod
    def validate_read_commands(cls, commands: list[str]) -> list[str]:
        """Chuẩn hóa và kiểm tra các lệnh chẩn đoán do Analyst Agent đề xuất.
        - Chỉ chấp nhận lệnh bắt đầu bằng show, ping hoặc traceroute.
        - Phát sinh ValueError nếu không có lệnh hợp lệ hoặc xuất hiện lệnh không thuộc nhóm được cho phép.
        """

        # Bước 1: Định nghĩa các lệnh được phép.
        allowed = ("show ", "ping ", "traceroute ")
        # Bước 2: Xác thực các lệnh đã chuẩn hóa.
        normalized = [
            command.strip()
            for command in commands
            if command.strip()
        ]
        # Bước 3: Kiểm tra các lệnh đã chuẩn hóa.
        if not normalized or any(
            not command.lower().startswith(allowed)
            for command in normalized
        ):
            raise ValueError(
                "Chỉ chấp nhận các lệnh chẩn đoán bắt đầu bằng "
                "'show ', 'ping ' hoặc 'traceroute '."
            )
        # Bước 4: Trả về danh sách các lệnh đã chuẩn hóa.
        return normalized


class AnalysisResult(BaseModel):
    """Kết quả phân tích của Analyst Agent, bao gồm tóm tắt, phát hiện, nguyên nhân có khả năng, khuyến nghị và yêu cầu thêm dữ liệu nếu cần."""
    summary: str = Field(max_length=600, description="Kết luận tổng thể bằng tiếng Việt, tối đa 600 ký tự.")
    findings: list[AnalysisItem] = Field(default_factory=list, max_length=4, description="Các phát hiện quan trọng dựa trên dữ liệu và bằng chứng đã thu thập." )
    likely_causes: list[AnalysisItem] = Field(default_factory=list, max_length=4, description="Các nguyên nhân có khả năng gây ra sự cố." )
    recommendations: list[AnalysisItem] = Field(default_factory=list, max_length=4, description="Các khuyến nghị hành động dựa trên phân tích." )
    requires_more_data: bool = Field(default=False, description="Cho biết có cần thu thập thêm dữ liệu để hoàn thiện chẩn đoán hay không.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Mức độ tin cậy của phân tích, từ 0.0 đến 1.0." )
    evidence_gaps: list[AnalysisItem] = Field(default_factory=list, max_length=4, description="Các khoảng trống trong bằng chứng." )
    suggested_checks: list[DiagnosticCheck] = Field(default_factory=list, max_length=4, description="Các phép kiểm tra được đề xuất." )
    is_anomaly: bool | None = Field(default=None, description="True nếu phát hiện bất thường, False nếu không, None nếu chưa đủ thông tin.")
    root_causes: list[PredictedRootCause] = Field(default_factory=list, max_length=8, description="Các nguyên nhân gốc đã được dự đoán." )
    suspected_causes: list[PredictedRootCause] = Field(default_factory=list, max_length=8, description="Các nguyên nhân nghi ngờ đã được dự đoán." )

