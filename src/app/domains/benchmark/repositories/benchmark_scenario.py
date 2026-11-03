"""Persistence contract và repository của benchmark_scenarios."""

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.audit.transaction import append_audit_in_session
from app.core.exceptions import ResourceNotFoundError
from app.domains.benchmark.models import BenchmarkScenarioModel
from app.domains.benchmark.schemas import BenchmarkScenarioRecord


class BenchmarkScenarioRepositoryProtocol(Protocol):
    def get_all(self) -> list[BenchmarkScenarioRecord]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all."""
        ...
    def get_by_id(self, scenario_id: str) -> BenchmarkScenarioRecord:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        ...
    def get_by_key(self, scenario_key: str) -> BenchmarkScenarioRecord | None:
        """Truy vấn scenario theo khóa nghiệp vụ ổn định."""
        ...
    def save(self, scenario: BenchmarkScenarioRecord) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save."""
        ...


class BenchmarkScenarioRepository:
    def __init__(self, database_url: str) -> None:
        """Khởi tạo BenchmarkScenarioRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    @staticmethod
    def _to_schema(model: BenchmarkScenarioModel) -> BenchmarkScenarioRecord:
        """Chuyển đổi dữ liệu nội bộ trong phương thức _to_schema."""
        return BenchmarkScenarioRecord.model_validate(
            {
                "id": model.id,
                "scenario_key": model.scenario_key,
                "version": model.version,
                "name": model.name,
                "description": model.description,
                "topology": model.topology,
                "initial_message": model.initial_message,
                **model.definition,
                "is_active": model.is_active,
                "created_by": model.created_by,
                "last_updated_by": model.last_updated_by,
                "created_at": model.created_at,
                "last_updated_at": model.last_updated_at,
            }
        )

    def get_all(self) -> list[BenchmarkScenarioRecord]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all."""
        with self._sessions() as session:
            rows = session.scalars(
                select(BenchmarkScenarioModel).order_by(BenchmarkScenarioModel.name)
            ).all()
            return [self._to_schema(row) for row in rows]

    def get_by_id(self, scenario_id: str) -> BenchmarkScenarioRecord:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        with self._sessions() as session:
            model = session.get(BenchmarkScenarioModel, scenario_id)
            if model is None:
                raise ResourceNotFoundError(
                    f"Không tìm thấy benchmark scenario '{scenario_id}'"
                )
            return self._to_schema(model)

    def get_by_key(self, scenario_key: str) -> BenchmarkScenarioRecord | None:
        """Truy vấn scenario theo khóa nghiệp vụ, không phân biệt hoa thường."""

        with self._sessions() as session:
            model = session.scalar(
                select(BenchmarkScenarioModel).where(
                    BenchmarkScenarioModel.scenario_key == scenario_key.casefold()
                )
            )
            return self._to_schema(model) if model is not None else None

    def save(self, scenario: BenchmarkScenarioRecord) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save."""
        definition_fields = {
            "preconditions",
            "injection",
            "fault_verification",
            "ground_truth",
            "evaluation_required_terms",
            "cleanup",
        }
        values = scenario.model_dump(exclude=definition_fields, mode="python")
        values["definition"] = scenario.model_dump(
            include=definition_fields, mode="json"
        )
        with self._sessions.begin() as session:
            append_audit_in_session(session)
            model = session.get(BenchmarkScenarioModel, scenario.id)
            if model is None:
                session.add(BenchmarkScenarioModel(**values))
            else:
                for key, value in values.items():
                    setattr(model, key, value)
