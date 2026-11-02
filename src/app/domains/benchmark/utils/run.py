"""Các hàm chuyển đổi dữ liệu của benchmark run."""

from app.domains.benchmark.schemas import BenchmarkRun, BenchmarkRunRecord


def to_public_benchmark_run(run: BenchmarkRunRecord) -> BenchmarkRun:
    """Loại bỏ dữ liệu nội bộ trước khi trả benchmark run cho API."""

    return BenchmarkRun.model_validate(run.model_dump())
