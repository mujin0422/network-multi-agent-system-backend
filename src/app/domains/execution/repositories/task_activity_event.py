"""Repository cho timeline trong bảng task_activity_events."""

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import TaskActivityEventModel
from app.domains.execution.schemas import TaskActivityEvent


class TaskActivityEventRepositoryProtocol(Protocol):
    def save_task_activity_event(self, event: TaskActivityEvent) -> None: ...
    def list_task_activity_events(self, task_id: str) -> list[TaskActivityEvent]: ...


class TaskActivityEventRepository:
    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def list_task_activity_events(self, task_id: str) -> list[TaskActivityEvent]:
        """Lấy timeline của Task theo sequence_number ổn định."""

        statement = (
            select(TaskActivityEventModel)
            .where(TaskActivityEventModel.task_id == task_id)
            .order_by(
                TaskActivityEventModel.sequence_number,
                TaskActivityEventModel.id,
            )
        )
        with self._sessions() as session:
            return [
                TaskActivityEvent.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]
    def save_task_activity_event(self, event: TaskActivityEvent) -> None:
        """Tạo hoặc cập nhật một mốc timeline."""

        with self._sessions.begin() as session:
            model = session.get(TaskActivityEventModel, event.id)
            if model is None:
                session.add(TaskActivityEventModel(**event.model_dump()))
                return
            for field, value in event.model_dump().items():
                setattr(model, field, value)

