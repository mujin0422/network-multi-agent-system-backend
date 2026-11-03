"""Repository cho User Session — quản lý phiên và rotate refresh token nguyên tử."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update

from app.core.database import create_session_factory
from app.domains.identity.models import UserSessionModel
from app.domains.identity.schemas import UserSessionRecord


class UserSessionRepository:
    
    def __init__(self, database_url: str) -> None:
        """Khởi tạo UserSessionRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def save_session(self, record: UserSessionRecord) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_session."""
        with self._sessions.begin() as session:
            session.add(
                UserSessionModel(
                    id=record.id,
                    user_id=record.user_id,
                    refresh_token_hash=record.refresh_token_hash,
                    expires_at=record.expires_at,
                    created_at=record.created_at,
                    revoked_at=record.revoked_at,
                )
            )


    def get_by_token_hash(self, token_hash: str) -> UserSessionRecord | None:
        """Lấy một UserSession theo refresh_token_hash, không phân biệt hoa thường."""
        with self._sessions() as session:
            model = session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.refresh_token_hash == token_hash
                )
            )
            return (
                UserSessionRecord.model_validate(model, from_attributes=True)
                if model is not None
                else None
            )


    def revoke_session(self, session_id: UUID, revoked_at: datetime) -> None:
        """Kết thúc hoặc loại bỏ dữ liệu theo nghiệp vụ của phương thức revoke_session."""
        statement = (
            update(UserSessionModel)
            .where(
                UserSessionModel.id == session_id, UserSessionModel.revoked_at.is_(None)
            )
            .values(revoked_at=revoked_at)
        )
        with self._sessions.begin() as session:
            session.execute(statement)


    def get_is_active(self, session_id: UUID) -> bool:
        """Kiểm tra một UserSession có đang hoạt động hay không."""
        return self.get_active_by_id(session_id) is not None


    def get_active_by_id(self, session_id: UUID) -> UserSessionRecord | None:
        """Lấy một UserSession theo ID nếu đang hoạt động (chưa bị revoke và chưa hết hạn)."""
        statement = select(UserSessionModel).where(
            UserSessionModel.id == session_id,
            UserSessionModel.revoked_at.is_(None),
            UserSessionModel.expires_at > datetime.now(UTC),
        )
        with self._sessions() as session:
            model = session.scalar(statement)
            return (
                UserSessionRecord.model_validate(model, from_attributes=True)
                if model is not None
                else None
            )


    def rotate_session(self, session_id: UUID, revoked_at: datetime, replacement: UserSessionRecord) -> bool:
        """Cập nhật dữ liệu theo nghiệp vụ của phương thức rotate_session."""
        statement = (
            update(UserSessionModel)
            .where(
                UserSessionModel.id == session_id,
                UserSessionModel.revoked_at.is_(None),
                UserSessionModel.expires_at > revoked_at,
            )
            .values(revoked_at=revoked_at)
        )
        with self._sessions.begin() as session:
            result = session.execute(statement)
            if result.rowcount != 1:
                return False
            session.add(
                UserSessionModel(
                    id=replacement.id,
                    user_id=replacement.user_id,
                    refresh_token_hash=replacement.refresh_token_hash,
                    expires_at=replacement.expires_at,
                    created_at=replacement.created_at,
                    revoked_at=replacement.revoked_at,
                )
            )
        return True
