"""Persistence contract và repository cho bảng task_operations."""

from typing import Any, Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import OperationModel
from app.domains.execution.schemas import Operation


class OperationRepositoryProtocol(Protocol):
    """Contract persistence của bảng task_operations."""

    def save_operation(self, operation: Operation) -> None: ...
    def get_operation(self, operation_id: str) -> Operation | None: ...
    def list_operations(self, task_id: str) -> list[Operation]: ...


class OperationRepository:
    """Quản lý các operation logic do Planner tạo."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def save_operation(self, operation: Operation) -> None:
        """Tạo mới hoặc cập nhật một operation."""

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
        """Lấy operation theo primary key để execution worker sử dụng."""

        with self._sessions() as session:
            model = session.get(OperationModel, operation_id)
            return Operation.model_validate(model, from_attributes=True) if model else None

    def list_operations(self, task_id: str) -> list[Operation]:
        """Lấy operations thuộc Task theo đúng display_order của Planner."""

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

    @staticmethod
    def add_all_in_session(session: Any, operations: list[Operation]) -> None:
        """Thêm operations bằng transaction chung của execution plan."""

        session.add_all(OperationModel(**item.model_dump()) for item in operations)
