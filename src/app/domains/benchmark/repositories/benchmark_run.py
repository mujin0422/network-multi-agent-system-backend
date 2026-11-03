"""Persistence contract và repository của benchmark_runs."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, func, select

from app.core.database import create_session_factory
from app.core.exceptions import ResourceNotFoundError
from app.domains.benchmark.models import BenchmarkRunModel
from app.domains.benchmark.schemas import BenchmarkRunRecord
from app.domains.benchmark.schemas.benchmark_run_summary import BenchmarkRunSummary
from app.domains.benchmark.utils.summary import summarize_run_groups
from app.domains.evaluation.models import TaskEvaluationMetricModel
from app.domains.evaluation.schemas import EvaluationMetricType


class BenchmarkRunRepositoryProtocol(Protocol):
    def get_summary(self) -> BenchmarkRunSummary:
        """Aggregate ALL runs by GOAL outcome, not the paginated list."""
        ...

    def get_all(self, limit: int = 50) -> list[BenchmarkRunRecord]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all."""
        ...
    def get_by_id(self, run_id: str) -> BenchmarkRunRecord:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        ...
    def get_by_source_message_id(self, source_message_id: str) -> BenchmarkRunRecord | None:
        """Find an active/completed run after its Chat workflow resumes."""
        ...
    def save(self, run: BenchmarkRunRecord) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save."""
        ...


class BenchmarkRunRepository:
    def __init__(self, database_url: str) -> None:
        """Khởi tạo BenchmarkRunRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    @staticmethod
    def _to_schema(model: BenchmarkRunModel) -> BenchmarkRunRecord:
        """Chuyển đổi dữ liệu nội bộ trong phương thức _to_schema."""
        return BenchmarkRunRecord.model_validate(
            {
                "id": model.id,
                "scenario_id": model.scenario_id,
                "scenario_version": model.scenario_version,
                "scenario_name": model.scenario_name,
                "scenario_snapshot": model.scenario_snapshot,
                "status": model.status,
                "started_by": model.started_by,
                "initial_message": model.initial_message,
                "conversation_id": model.conversation_id,
                "source_message_id": model.source_message_id,
                "task_id": model.task_id,
                "evaluation_id": str(model.evaluation_id) if model.evaluation_id else None,
                "evaluation_result": model.evaluation_result,
                "cleanup_required": model.cleanup_required,
                "error_message": model.error_message,
                "started_at": model.started_at,
                "completed_at": model.completed_at,
                "cleaned_at": model.cleaned_at,
            }
        )

    def get_summary(self) -> BenchmarkRunSummary:
        """SQL GROUP BY across the entire history; prevent 100-row sample bias."""
        has_source = BenchmarkRunModel.source_message_id.is_not(None)
        has_evaluation = BenchmarkRunModel.evaluation_id.is_not(None)
        has_error = BenchmarkRunModel.error_message.is_not(None)
        goal_result = TaskEvaluationMetricModel.result
        statement = (
            select(
                BenchmarkRunModel.status,
                has_source.label("has_source"),
                has_evaluation.label("has_evaluation"),
                goal_result,
                has_error.label("has_error"),
                func.count(BenchmarkRunModel.id),
            )
            .outerjoin(
                TaskEvaluationMetricModel,
                and_(
                    TaskEvaluationMetricModel.evaluation_id
                    == BenchmarkRunModel.evaluation_id,
                    TaskEvaluationMetricModel.metric_type == EvaluationMetricType.GOAL,
                ),
            )
            .group_by(
                BenchmarkRunModel.status,
                has_source,
                has_evaluation,
                goal_result,
                has_error,
            )
        )
        with self._sessions() as session:
            grouped_rows = session.execute(statement).all()
        return summarize_run_groups([
            (
                str(status),
                bool(source),
                bool(evaluation),
                (result.value if hasattr(result, "value") else result),
                bool(error),
                int(count),
            )
            for status, source, evaluation, result, error, count in grouped_rows
        ])

    def get_all(self, limit: int = 50) -> list[BenchmarkRunRecord]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all."""
        with self._sessions() as session:
            rows = session.scalars(
                select(BenchmarkRunModel)
                .order_by(BenchmarkRunModel.started_at.desc())
                .limit(limit)
            ).all()
            return [self._to_schema(row) for row in rows]

    def get_by_id(self, run_id: str) -> BenchmarkRunRecord:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        with self._sessions() as session:
            model = session.get(BenchmarkRunModel, run_id)
            if model is None:
                raise ResourceNotFoundError(f"Không tìm thấy benchmark run '{run_id}'")
            return self._to_schema(model)

    def get_by_source_message_id(self, source_message_id: str) -> BenchmarkRunRecord | None:
        with self._sessions() as session:
            model = session.scalar(
                select(BenchmarkRunModel).where(
                    BenchmarkRunModel.source_message_id == source_message_id
                )
            )
            return self._to_schema(model) if model is not None else None

    def save(self, run: BenchmarkRunRecord) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save."""
        values = run.model_dump(exclude={"scenario_snapshot"}, mode="python")
        values["status"] = run.status.value
        values["scenario_snapshot"] = run.scenario_snapshot.model_dump(mode="json")
        values["evaluation_id"] = UUID(run.evaluation_id) if run.evaluation_id else None
        with self._sessions.begin() as session:
            model = session.get(BenchmarkRunModel, run.id)
            if model is None:
                session.add(BenchmarkRunModel(**values))
            else:
                for key, value in values.items():
                    setattr(model, key, value)
