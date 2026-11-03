"""Repository cho bảng task_evaluation_metrics."""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.evaluation.models import TaskEvaluationMetricModel
from app.domains.evaluation.schemas import TaskEvaluationMetric


class TaskEvaluationMetricRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo factory tạo session kết nối cơ sở dữ liệu."""
        self._sessions = create_session_factory(database_url)


    def get_all_by_evaluation_id(self, evaluation_id: UUID) -> list[TaskEvaluationMetric]:
        """Lấy toàn bộ metric của một Task Evaluation."""
        return self.get_all_by_evaluation_ids([evaluation_id])


    def get_all_by_evaluation_ids(self, evaluation_ids: Iterable[UUID]) -> list[TaskEvaluationMetric]:
        """Lấy metric thuộc nhiều Evaluation bằng một truy vấn."""
        ids = list(evaluation_ids)
        if not ids:
            return []
        statement = (
            select(TaskEvaluationMetricModel)
            .where(TaskEvaluationMetricModel.evaluation_id.in_(ids))
            .order_by(
                TaskEvaluationMetricModel.evaluation_id,
                TaskEvaluationMetricModel.metric_type,
            )
        )
        with self._sessions() as session:
            return [
                TaskEvaluationMetric.model_validate(row, from_attributes=True)
                for row in session.scalars(statement).all()
            ]


    def save(self, metrics: list[TaskEvaluationMetric]) -> None:
        """Lưu danh sách metric trong transaction độc lập."""
        with self._sessions.begin() as session:
            session.add_all(
                TaskEvaluationMetricModel(**metric.model_dump()) for metric in metrics
            )
