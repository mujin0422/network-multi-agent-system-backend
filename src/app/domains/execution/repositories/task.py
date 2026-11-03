"""Repository cho bảng tasks."""

from typing import Any

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import TaskModel
from app.domains.execution.schemas import Task, TaskStatus


class TaskRepository:
    """Quản lý vòng đời record thuộc bảng tasks."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo TaskRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    def save_task(self, task: Task) -> None:
        """Tạo/cập nhật Task trong một transaction độc lập."""

        with self._sessions.begin() as session:
            self.save_in_session(session, task)

    @staticmethod
    def save_in_session(session: Any, task: Task) -> None:
        """Tạo/cập nhật Task bằng session do Unit of Work cung cấp.

        Method này không commit để Task có thể được lưu nguyên tử cùng toàn bộ
        execution plan trong ``ExecutionRepository.save_execution_plan``.
        """

        model = session.get(TaskModel, task.id, with_for_update=True)
        if model is None:
            session.add(TaskModel(**task.model_dump()))
            return
        # Terminal tasks are immutable: reject even a stale SUCCESS callback
        # after timeout was committed as FAILED or PARTIAL_SUCCESS.
        if model.task_status in {
            TaskStatus.SUCCESS, TaskStatus.PARTIAL_SUCCESS,
            TaskStatus.FAILED, TaskStatus.REJECTED,
        }:
            return
        model.conversation_id = task.conversation_id
        model.source_message_id = task.source_message_id
        model.user_id = task.user_id
        model.input_message = task.input_message
        model.task_status = task.task_status
        model.task_type = task.task_type
        model.started_at = task.started_at
        model.completed_at = task.completed_at

    def get_by_id(self, task_id: str) -> Task | None:
        """Lấy Task theo primary key."""

        with self._sessions() as session:
            model = session.get(TaskModel, task_id)
            return Task.model_validate(model, from_attributes=True) if model else None

    def get_all(self) -> list[Task]:
        """Lấy danh sách Task, Task mới nhất đứng trước."""

        statement = select(TaskModel).order_by(TaskModel.created_at.desc(), TaskModel.id)
        with self._sessions() as session:
            return [
                Task.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]

    def get_by_source_message_id(self, message_id: str) -> Task | None:
        """Tìm Task đã được tạo từ USER message để chống tạo trùng."""

        statement = select(TaskModel).where(TaskModel.source_message_id == message_id)
        with self._sessions() as session:
            model = session.scalar(statement)
            return Task.model_validate(model, from_attributes=True) if model else None
