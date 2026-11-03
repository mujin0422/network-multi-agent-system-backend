"""Persistence cho kết quả đánh giá Task."""

from typing import Protocol
from uuid import UUID

from app.core.database import create_session_factory
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.evaluation.models import (
    TaskEvaluationMetricModel,
    TaskEvaluationModel,
)
from app.domains.evaluation.schemas import (
    TaskEvaluationDetail,
    TaskEvaluationMetric,
    TaskEvaluationSummary,
)


class TaskEvaluationRepositoryProtocol(Protocol):
    def save(self, evaluation: TaskEvaluationDetail) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save."""
        ...
    def get_by_id(self, evaluation_id: UUID) -> TaskEvaluationDetail | None:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        ...
    def get_by_task_id(self, task_id: str) -> TaskEvaluationDetail | None:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_task_id."""
        ...

    def get_recent(self, limit: int = 50) -> list[TaskEvaluationSummary]:
        """Danh sách Evaluation mới nhất kèm trạng thái các metric, không có evidence."""
        ...


class TaskEvaluationRepository:
    def __init__(self, database_url: str) -> None:
        """Khởi tạo TaskEvaluationRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    def save(self, evaluation: TaskEvaluationDetail) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save."""
        with self._sessions.begin() as session:
            self.save_in_session(session, evaluation)

    @staticmethod
    def save_in_session(session: Session, evaluation: TaskEvaluationDetail) -> None:
        """Save evaluation and metrics inside caller-owned transaction."""
        session.add(
            TaskEvaluationModel(**evaluation.model_dump(exclude={"metrics"}))
        )
        session.add_all(
            TaskEvaluationMetricModel(**metric.model_dump())
            for metric in evaluation.metrics
        )

    def get_by_id(self, evaluation_id: UUID) -> TaskEvaluationDetail | None:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        with self._sessions() as session:
            model = session.get(TaskEvaluationModel, evaluation_id)
            return self._to_schema(session, model)

    def get_by_task_id(self, task_id: str) -> TaskEvaluationDetail | None:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_task_id."""
        with self._sessions() as session:
            model = session.scalar(
                select(TaskEvaluationModel).where(
                    TaskEvaluationModel.task_id == task_id
                )
            )
            return self._to_schema(session, model)

    def get_recent(self, limit: int = 50) -> list[TaskEvaluationSummary]:
        """Nạp Evaluation và metric bằng hai truy vấn, không lộ evidence."""

        with self._sessions() as session:
            rows = session.scalars(
                select(TaskEvaluationModel)
                .order_by(TaskEvaluationModel.created_at.desc(), TaskEvaluationModel.id)
                .limit(min(max(limit, 1), 100))
            ).all()
            if not rows:
                return []
            metric_rows = session.scalars(
                select(TaskEvaluationMetricModel).where(
                    TaskEvaluationMetricModel.evaluation_id.in_(
                        [item.id for item in rows]
                    )
                )
            ).all()
            results_by_id: dict[UUID, dict] = {item.id: {} for item in rows}
            for metric in metric_rows:
                results_by_id[metric.evaluation_id][metric.metric_type] = metric.result
            return [
                TaskEvaluationSummary.model_validate(
                    {
                        "id": row.id,
                        "task_id": row.task_id,
                        "evaluation_status": row.evaluation_status,
                        "evaluator_type": row.evaluator_type,
                        "evaluator_version": row.evaluator_version,
                        "created_at": row.created_at,
                        "evaluated_at": row.evaluated_at,
                        "results": results_by_id[row.id],
                    }
                )
                for row in rows
            ]

    @staticmethod
    def _to_schema(
        session, model: TaskEvaluationModel | None
    ) -> TaskEvaluationDetail | None:
        """Chuyển đổi dữ liệu nội bộ trong phương thức _to_schema."""
        if model is None:
            return None
        metrics = session.scalars(
            select(TaskEvaluationMetricModel)
            .where(TaskEvaluationMetricModel.evaluation_id == model.id)
            .order_by(TaskEvaluationMetricModel.metric_type)
        ).all()
        return TaskEvaluationDetail.model_validate(
            {
                "id": model.id,
                "task_id": model.task_id,
                "evaluation_status": model.evaluation_status,
                "evaluator_type": model.evaluator_type,
                "evaluator_version": model.evaluator_version,
                "created_at": model.created_at,
                "evaluated_at": model.evaluated_at,
                "metrics": [
                    TaskEvaluationMetric.model_validate(item, from_attributes=True)
                    for item in metrics
                ],
            }
        )
