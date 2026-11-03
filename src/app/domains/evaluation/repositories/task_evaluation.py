"""Repository cho bảng task_evaluations."""

from uuid import UUID

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.evaluation.models import TaskEvaluationModel
from app.domains.evaluation.schemas import TaskEvaluation


class TaskEvaluationRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo factory tạo session kết nối cơ sở dữ liệu."""
        self._sessions = create_session_factory(database_url)


    def get_by_id(self, evaluation_id: UUID) -> TaskEvaluation | None:
        """Lấy Task Evaluation theo ID."""
        with self._sessions() as session:
            model = session.get(TaskEvaluationModel, evaluation_id)
            return (
                TaskEvaluation.model_validate(model, from_attributes=True)
                if model is not None
                else None
            )


    def get_by_task_id(self, task_id: str) -> TaskEvaluation | None:
        """Lấy Task Evaluation duy nhất của một Task."""
        statement = select(TaskEvaluationModel).where(
            TaskEvaluationModel.task_id == task_id
        )
        with self._sessions() as session:
            model = session.scalar(statement)
            return (
                TaskEvaluation.model_validate(model, from_attributes=True)
                if model is not None
                else None
            )


    def get_recent(self, limit: int = 50) -> list[TaskEvaluation]:
        """Lấy các Task Evaluation mới nhất, giới hạn tối đa 100 bản ghi."""
        statement = (
            select(TaskEvaluationModel)
            .order_by(TaskEvaluationModel.created_at.desc(), TaskEvaluationModel.id)
            .limit(min(max(limit, 1), 100))
        )
        with self._sessions() as session:
            return [
                TaskEvaluation.model_validate(row, from_attributes=True)
                for row in session.scalars(statement).all()
            ]


    def save(self, evaluation: TaskEvaluation) -> None:
        """Lưu Task Evaluation trong transaction độc lập."""
        with self._sessions.begin() as session:
            session.add(
                TaskEvaluationModel(**evaluation.model_dump(exclude={"metrics"}))
            )
