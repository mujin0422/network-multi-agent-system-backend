"""Repository của bảng benchmark_runs."""

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


class BenchmarkRunRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo BenchmarkRunRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


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
            return [
                BenchmarkRunRecord.model_validate(row, from_attributes=True)
                for row in rows
            ]


    def get_page(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[BenchmarkRunRecord], int]:
        """Lấy một trang benchmark run và tổng số bản ghi trong lịch sử."""

        data_statement = (
            select(BenchmarkRunModel)
            .order_by(BenchmarkRunModel.started_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_statement = select(func.count()).select_from(BenchmarkRunModel)
        with self._sessions() as session:
            rows = session.scalars(data_statement).all()
            total = session.scalar(count_statement) or 0
            return (
                [
                    BenchmarkRunRecord.model_validate(row, from_attributes=True)
                    for row in rows
                ],
                int(total),
            )


    def get_by_id(self, run_id: str) -> BenchmarkRunRecord:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        with self._sessions() as session:
            model = session.get(BenchmarkRunModel, run_id)
            if model is None:
                raise ResourceNotFoundError(f"Không tìm thấy benchmark run '{run_id}'")
            return BenchmarkRunRecord.model_validate(model, from_attributes=True)


    def get_by_source_message_id(self, source_message_id: str) -> BenchmarkRunRecord | None:
        """Lấy benchmark run được tạo từ một message."""

        with self._sessions() as session:
            model = session.scalar(
                select(BenchmarkRunModel).where(
                    BenchmarkRunModel.source_message_id == source_message_id
                )
            )
            return (
                BenchmarkRunRecord.model_validate(model, from_attributes=True)
                if model is not None
                else None
            )


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
