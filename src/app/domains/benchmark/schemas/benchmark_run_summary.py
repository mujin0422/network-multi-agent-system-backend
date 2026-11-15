"""Aggregate Goal-based task success rate over all benchmark runs."""

from pydantic import BaseModel, Field


class BenchmarkRunSummary(BaseModel):
    """Tổng hợp kết quả benchmark run theo từng scenario."""
    total_runs: int = Field(ge=0, description="Tổng số lần chạy benchmark.")
    passed: int = Field(ge=0, description="Số lần chạy benchmark thành công.")
    failed: int = Field(ge=0, description="Số lần chạy benchmark thất bại.")
    in_progress: int = Field(ge=0, description="Số lần chạy benchmark đang tiến hành.")
    not_started: int = Field(ge=0, description="Số lần chạy benchmark chưa bắt đầu.")
    setup_failed: int = Field(ge=0, description="Số lần chạy benchmark thất bại trong quá trình thiết lập.")
    unscored: int = Field(ge=0, description="Số lần chạy benchmark không được chấm điểm.")
    eligible_runs: int = Field(ge=0, description="Số lần chạy benchmark đủ điều kiện để được chấm điểm.")
    success_rate: float | None = Field(default=None, ge=0, le=100, description="Tỷ lệ thành công của các lần chạy benchmark.")