"""Persistence contract và PostgreSQL adapter của Execution domain."""

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import OperationModel, TaskModel
from app.domains.execution.schemas import Operation, Task


class ExecutionRepository(Protocol):
    def save_task(self, task: Task) -> None: ...

    def get_task(self, task_id: str) -> Task | None: ...

    def list_tasks(self) -> list[Task]: ...

    def find_task_by_source_message(self, message_id: str) -> Task | None: ...

    def save_operation(self, operation: Operation) -> None: ...

    def get_operation(self, operation_id: str) -> Operation | None: ...

    def list_operations(self, task_id: str) -> list[Operation]: ...


class PostgresExecutionRepository:
    """Execution repository được triển khai bằng SQLAlchemy ORM."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def save_task(self, task: Task) -> None:
        with self._sessions.begin() as session:
            model = session.get(TaskModel, task.id)
            if model is None:
                session.add(TaskModel(**task.model_dump()))
                return
            model.conversation_id = task.conversation_id
            model.source_message_id = task.source_message_id
            model.user_id = task.user_id
            model.input_message = task.input_message
            model.task_status = task.task_status
            model.task_type = task.task_type
            model.started_at = task.started_at
            model.completed_at = task.completed_at

    def get_task(self, task_id: str) -> Task | None:
        with self._sessions() as session:
            model = session.get(TaskModel, task_id)
            return Task.model_validate(model, from_attributes=True) if model else None

    def list_tasks(self) -> list[Task]:
        statement = select(TaskModel).order_by(TaskModel.created_at.desc(), TaskModel.id)
        with self._sessions() as session:
            return [
                Task.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]

    def find_task_by_source_message(self, message_id: str) -> Task | None:
        statement = select(TaskModel).where(TaskModel.source_message_id == message_id)
        with self._sessions() as session:
            model = session.scalar(statement)
            return Task.model_validate(model, from_attributes=True) if model else None

    def save_operation(self, operation: Operation) -> None:
        with self._sessions.begin() as session:
            model = session.get(OperationModel, operation.id)
            if model is None:
                session.add(OperationModel(**operation.model_dump()))
                return
            model.task_id = operation.task_id
            model.operation_intent = operation.operation_intent
            model.display_order = operation.display_order
            model.operation_status = operation.operation_status
            model.operation_parameters = operation.operation_parameters
            model.started_at = operation.started_at
            model.completed_at = operation.completed_at

    def get_operation(self, operation_id: str) -> Operation | None:
        with self._sessions() as session:
            model = session.get(OperationModel, operation_id)
            return (
                Operation.model_validate(model, from_attributes=True)
                if model
                else None
            )

    def list_operations(self, task_id: str) -> list[Operation]:
        statement = (
            select(OperationModel)
            .where(OperationModel.task_id == task_id)
            .order_by(OperationModel.display_order, OperationModel.id)
        )
        with self._sessions() as session:
            return [
                Operation.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]
