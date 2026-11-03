"""Use cases quản lý benchmark_scenarios."""

from datetime import UTC, datetime

from app.core.exceptions import ResourceConflictError
from app.core.utils import IdPrefix, generate_id
from app.domains.benchmark.repositories import BenchmarkScenarioRepositoryProtocol
from app.domains.benchmark.schemas import (
    BenchmarkScenario,
    BenchmarkScenarioRecord,
    BenchmarkScenarioSummary,
    BenchmarkScenarioUpdate,
)


class BenchmarkScenarioService:
    def __init__(self, repository: BenchmarkScenarioRepositoryProtocol) -> None:
        """Khởi tạo BenchmarkScenarioService cùng các phụ thuộc cần thiết."""
        self._repository = repository

    def list(self) -> list[BenchmarkScenarioSummary]:
        """Truy vấn danh sách dữ liệu theo phạm vi của phương thức list."""
        return [
            BenchmarkScenarioSummary.model_validate(scenario.model_dump())
            for scenario in self._repository.get_all()
        ]

    def get(self, scenario_id: str) -> BenchmarkScenarioRecord:
        """Lấy đủ các bước inject/verify/cleanup để chỉnh sửa một scenario."""

        return self._repository.get_by_id(scenario_id)

    def create(
        self, payload: BenchmarkScenario, user_id: str
    ) -> BenchmarkScenarioRecord:
        """Tạo mới dữ liệu theo nghiệp vụ của phương thức create."""
        if self._repository.get_by_key(payload.scenario_key) is not None:
            raise ResourceConflictError(
                f"Benchmark scenario key '{payload.scenario_key}' đã tồn tại"
            )
        now = datetime.now(UTC)
        record = BenchmarkScenarioRecord(
            id=generate_id(IdPrefix.BENCHMARK_SCENARIO),
            **payload.model_dump(),
            is_active=True,
            created_by=user_id,
            last_updated_by=user_id,
            created_at=now,
            last_updated_at=now,
        )
        self._repository.save(record)
        return record

    def update(
        self, scenario_id: str, payload: BenchmarkScenarioUpdate, user_id: str
    ) -> BenchmarkScenarioRecord:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức update."""
        current = self._repository.get_by_id(scenario_id)
        updated = current.model_copy(
            update={
                **payload.model_dump(exclude_unset=True),
                "last_updated_by": user_id,
                "last_updated_at": datetime.now(UTC),
            }
        )
        validated = BenchmarkScenarioRecord.model_validate(updated.model_dump())
        self._repository.save(validated)
        return validated
