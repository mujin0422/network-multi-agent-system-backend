"""Public ORM models của Benchmark domain."""

from app.domains.benchmark.models.benchmark_run import BenchmarkRunModel
from app.domains.benchmark.models.benchmark_scenario import BenchmarkScenarioModel

__all__ = ["BenchmarkRunModel", "BenchmarkScenarioModel"]
