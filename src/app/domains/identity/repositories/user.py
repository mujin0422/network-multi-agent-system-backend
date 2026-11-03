"""Repository cho User — bảng users."""

from datetime import datetime
from sqlalchemy import select, update

from app.core.database import create_session_factory
from app.domains.identity.models import UserModel
from app.domains.identity.schemas import User, UserRecord


class UserRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo UserRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    @staticmethod
    def _user_record(model: UserModel | None) -> UserRecord | None:
        """Chuyển đổi dữ liệu nội bộ trong phương thức _user_record."""
        return UserRecord.model_validate(model, from_attributes=True) if model else None


    def get_by_email(self, email: str) -> UserRecord | None:
        """Lấy một User theo email, không phân biệt hoa thường."""
        with self._sessions() as session:
            return self._user_record(
                session.scalar(
                    select(UserModel).where(UserModel.email == email.lower())
                )
            )


    def get_by_id(self, user_id: str) -> User | None:
        """Lấy một User theo primary key."""
        with self._sessions() as session:
            model = session.get(UserModel, user_id)
            return User.model_validate(model, from_attributes=True) if model else None


    def get_all(self) -> list[User]:
        """Lấy toàn bộ User từ database, sắp xếp theo id."""
        with self._sessions() as session:
            models = session.scalars(select(UserModel)).all()
            return [
                User.model_validate(model, from_attributes=True) for model in models
            ]


    def get_record_by_id(self, user_id: str) -> UserRecord | None:
        """Lấy một UserRecord theo primary key."""
        with self._sessions() as session:
            return self._user_record(session.get(UserModel, user_id))


    def save_user(self, record: UserRecord) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_user."""
        with self._sessions.begin() as session:
            model = session.get(UserModel, record.id)
            if model is None:
                session.add(
                    UserModel(
                        id=record.id,
                        role_id=record.role_id,
                        email=record.email,
                        password_hash=record.password_hash,
                        full_name=record.full_name,
                        user_status=record.user_status,
                        created_at=record.created_at,
                        last_updated_at=record.last_updated_at,
                        last_login_at=record.last_login_at,
                    )
                )
                return
            model.role_id = record.role_id
            model.email = record.email
            model.password_hash = record.password_hash
            model.full_name = record.full_name
            model.user_status = record.user_status
            model.last_updated_at = record.last_updated_at
            model.last_login_at = record.last_login_at


    def update_login(self, user_id: str, logged_in_at: datetime) -> None:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức update_login."""
        statement = (
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(last_login_at=logged_in_at)
        )
        with self._sessions.begin() as session:
            session.execute(statement)
