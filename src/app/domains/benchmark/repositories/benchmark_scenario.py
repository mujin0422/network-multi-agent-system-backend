"""Repository của bảng benchmark_scenarios."""

from sqlalchemy import select

from app.core.database import create_session_factory
from app.core.exceptions import ResourceNotFoundError
from app.domains.benchmark.models import BenchmarkScenarioModel
from app.domains.benchmark.schemas import BenchmarkScenarioRecord


class BenchmarkScenarioRepository:
    
    def __init__(self, database_url: str) -> None:
        """Khởi tạo BenchmarkScenarioRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def get_all(self) -> list[BenchmarkScenarioRecord]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all."""
        with self._sessions() as session:
            rows = session.scalars(
                select(BenchmarkScenarioModel).order_by(BenchmarkScenarioModel.name)
            ).all()
            return [
                BenchmarkScenarioRecord.model_validate(row, from_attributes=True)
                for row in rows
            ]


    def get_by_id(self, scenario_id: str) -> BenchmarkScenarioRecord:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        with self._sessions() as session:
            model = session.get(BenchmarkScenarioModel, scenario_id)
            if model is None:
                raise ResourceNotFoundError(
                    f"Không tìm thấy benchmark scenario '{scenario_id}'"
                )
            return BenchmarkScenarioRecord.model_validate(model, from_attributes=True)


    def get_by_key(self, scenario_key: str) -> BenchmarkScenarioRecord | None:
        """Truy vấn scenario theo khóa nghiệp vụ, không phân biệt hoa thường."""

        with self._sessions() as session:
            model = session.scalar(
                select(BenchmarkScenarioModel).where(
                    BenchmarkScenarioModel.scenario_key == scenario_key.casefold()
                )
            )
            return (
                BenchmarkScenarioRecord.model_validate(model, from_attributes=True)
                if model is not None
                else None
            )


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
            model = session.get(BenchmarkScenarioModel, scenario.id)
            if model is None:
                session.add(BenchmarkScenarioModel(**values))
            else:
                for key, value in values.items():
                    setattr(model, key, value)
