"""Repository cho bảng operation_dependencies."""

from typing import Any

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import OperationDependencyModel
from app.domains.execution.schemas import OperationDependency


class OperationDependencyRepository:
    """Ghi dependency graph giữa các operation của cùng một Task."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def list_dependencies(self, operation_id: str) -> list[OperationDependency]:
        """Lấy các operation tiên quyết của một operation."""

        statement = select(OperationDependencyModel).where(
            OperationDependencyModel.operation_id == operation_id
        )
        with self._sessions() as session:
            return [
                OperationDependency.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]

    @staticmethod
    def add_all_in_session(
        session: Any,
        dependencies: list[OperationDependency],
    ) -> None:
        """Thêm dependencies bằng session chung, không tự commit transaction."""

        session.add_all(
            OperationDependencyModel(**item.model_dump()) for item in dependencies
        )
