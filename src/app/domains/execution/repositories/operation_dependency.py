"""Repository cho bảng operation_dependencies."""

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import OperationDependencyModel
from app.domains.execution.schemas import OperationDependency


class OperationDependencyRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo OperationDependencyRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def get_all_by_operation_id(self, operation_id: str,) -> list[OperationDependency]:
        """Lấy các operation tiên quyết của một operation."""
        statement = select(OperationDependencyModel).where(
            OperationDependencyModel.operation_id == operation_id
        )
        with self._sessions() as session:
            return [
                OperationDependency.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]

    def get_all_by_operation_ids(
        self,
        operation_ids: list[str],
    ) -> list[OperationDependency]:
        """Lấy dependency của nhiều Operation bằng một truy vấn."""

        if not operation_ids:
            return []
        statement = (
            select(OperationDependencyModel)
            .where(OperationDependencyModel.operation_id.in_(operation_ids))
            .order_by(
                OperationDependencyModel.operation_id,
                OperationDependencyModel.depends_on_operation_id,
            )
        )
        with self._sessions() as session:
            return [
                OperationDependency.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]


    def save(self, dependencies: list[OperationDependency]) -> None:
        """Lưu danh sách dependency trong một transaction."""
        with self._sessions.begin() as session:
            session.add_all(
                OperationDependencyModel(**item.model_dump()) for item in dependencies
            )
