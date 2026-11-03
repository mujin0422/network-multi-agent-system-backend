"""Repository cho Role — bảng roles."""

from sqlalchemy import func, select

from app.core.database import create_session_factory
from app.domains.identity.models import RoleModel
from app.domains.identity.schemas import Role


class RoleRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo RoleRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def get_by_id(self, role_id: str) -> Role | None:
        """Lấy một Role theo primary key."""
        with self._sessions() as session:
            model = session.get(RoleModel, role_id)
            return Role.model_validate(model, from_attributes=True) if model else None


    def get_all(self) -> list[Role]:
        """Lấy toàn bộ Role từ database, sắp xếp theo id."""
        with self._sessions() as session:
            models = session.scalars(select(RoleModel)).all()
            return [
                Role.model_validate(model, from_attributes=True) for model in models
            ]


    def get_by_name(self, name: str) -> Role | None:
        """Lấy một Role theo name, không phân biệt hoa thường."""
        statement = select(RoleModel).where(func.lower(RoleModel.name) == name.lower())
        with self._sessions() as session:
            model = session.scalar(statement)
            return Role.model_validate(model, from_attributes=True) if model else None


    def save_role(self, record: Role) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_role."""
        with self._sessions.begin() as session:
            model = session.get(RoleModel, record.id)
            if model is None:
                session.add(RoleModel(**record.model_dump()))
                return
            model.name = record.name
            model.description = record.description
            model.last_updated_by = record.last_updated_by
            model.last_updated_at = record.last_updated_at
