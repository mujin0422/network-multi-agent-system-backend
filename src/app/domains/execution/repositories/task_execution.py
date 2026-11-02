"""Repository cho metadata mỗi lần Agent/Tool thực thi."""

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
