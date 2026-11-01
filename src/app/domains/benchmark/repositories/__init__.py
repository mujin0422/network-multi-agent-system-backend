"""Public persistence contracts của Benchmark domain."""

from app.domains.benchmark.repositories.benchmark_run import (
    BenchmarkRunRepository,
    BenchmarkRunRepositoryProtocol,
)
from app.domains.benchmark.repositories.benchmark_scenario import (
    BenchmarkScenarioRepository,
    BenchmarkScenarioRepositoryProtocol,
)

__all__ = [
    "BenchmarkRunRepository",
    "BenchmarkRunRepositoryProtocol",
    "BenchmarkScenarioRepository",
    "BenchmarkScenarioRepositoryProtocol",
]
