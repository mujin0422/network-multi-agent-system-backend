"""Use cases quản lý benchmark_scenarios."""

from datetime import UTC, datetime

from app.domains.audit.transaction import audit_mutation, record_audit_in_session
from app.core.database import DatabaseUnitOfWork

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
    def __init__(
        self, repository: BenchmarkScenarioRepositoryProtocol,
        uow: DatabaseUnitOfWork | None = None,
    ) -> None:
        """Khởi tạo BenchmarkScenarioService cùng các phụ thuộc cần thiết."""
        self._repository = repository
        self._uow = uow

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
        if self._uow is None:
            with audit_mutation("BENCHMARK_SCENARIO_CREATE", "BENCHMARK_SCENARIO", record.id, actor_user_id=user_id):
                self._repository.save(record)
        else:
            with self._uow.begin() as session:
                self._repository.save_in_session(session, record)
                record_audit_in_session(
                    session, action="BENCHMARK_SCENARIO_CREATE",
                    resource_type="BENCHMARK_SCENARIO", resource_id=record.id,
                    actor_user_id=user_id,
                )
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
        if self._uow is None:
            with audit_mutation("BENCHMARK_SCENARIO_UPDATE", "BENCHMARK_SCENARIO", validated.id, actor_user_id=user_id):
                self._repository.save(validated)
        else:
            with self._uow.begin() as session:
                self._repository.save_in_session(session, validated)
                record_audit_in_session(
                    session, action="BENCHMARK_SCENARIO_UPDATE",
                    resource_type="BENCHMARK_SCENARIO", resource_id=validated.id,
                    actor_user_id=user_id,
                )
        return validated
