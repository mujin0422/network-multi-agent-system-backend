"""Repository cho metadata mỗi lần Agent/Tool thực thi."""

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import TaskExecutionModel
from app.domains.execution.schemas import TaskExecution


class TaskExecutionRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo TaskExecutionRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def save(self, execution: TaskExecution) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save."""
        with self._sessions.begin() as session:
            model = session.get(TaskExecutionModel, execution.id)
            if model is None:
                session.add(TaskExecutionModel(**execution.model_dump()))
                return
            for field, value in execution.model_dump().items():
                setattr(model, field, value)


    def get_all_by_task_id(self, task_id: str) -> list[TaskExecution]:
        """Lấy mọi lượt Agent/Tool thực thi thuộc một Task theo thứ tự bước."""
        statement = (
            select(TaskExecutionModel)
            .where(TaskExecutionModel.task_id == task_id)
            .order_by(
                TaskExecutionModel.step_order,
                TaskExecutionModel.created_at,
                TaskExecutionModel.id,
            )
        )
        with self._sessions() as session:
            return [
                TaskExecution.model_validate(row, from_attributes=True)
                for row in session.scalars(statement).all()
            ]
