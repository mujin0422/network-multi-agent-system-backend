"""Repository cho bảng messages."""

from datetime import datetime

from sqlalchemy import and_, or_, select

from app.core.database import create_session_factory
from app.domains.conversation.models import MessageModel
from app.domains.conversation.schemas import Message


class MessageRepository:
    """Đọc và ghi duy nhất bảng messages."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo MessageRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def save(self, message: Message) -> None:
        """Lưu một message mới; bảng messages không có use case update."""

        with self._sessions.begin() as session:
            session.add(MessageModel(**message.model_dump()))


    def get_all_by_conversation_id(self, conversation_id: str) -> list[Message]:
        """Lấy lịch sử message của một conversation theo thứ tự thời gian."""

        statement = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            # ID là tie-breaker khi hai message có cùng timestamp.
            .order_by(MessageModel.created_at, MessageModel.id)
        )
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [
                Message.model_validate(item, from_attributes=True)
                for item in models
            ]

    def get_page_by_conversation_id(
        self,
        conversation_id: str,
        *,
        limit: int,
        before_created_at: datetime | None = None,
        before_id: str | None = None,
    ) -> tuple[list[Message], bool]:
        """Lấy message cũ dần bằng keyset pagination và trả theo chiều thời gian."""

        statement = select(MessageModel).where(
            MessageModel.conversation_id == conversation_id
        )
        if before_created_at is not None and before_id is not None:
            statement = statement.where(
                or_(
                    MessageModel.created_at < before_created_at,
                    and_(
                        MessageModel.created_at == before_created_at,
                        MessageModel.id < before_id,
                    ),
                )
            )
        statement = statement.order_by(
            MessageModel.created_at.desc(),
            MessageModel.id.desc(),
        ).limit(limit + 1)
        with self._sessions() as session:
            models = list(session.scalars(statement).all())
        has_more = len(models) > limit
        items = [
            Message.model_validate(item, from_attributes=True)
            for item in reversed(models[:limit])
        ]
        return items, has_more

    def get_recent_before(
        self,
        conversation_id: str,
        *,
        before_created_at: datetime,
        before_id: str,
        limit: int,
    ) -> list[Message]:
        """Lấy tối đa ``limit`` message ngay trước một message theo thời gian."""

        statement = (
            select(MessageModel)
            .where(
                MessageModel.conversation_id == conversation_id,
                or_(
                    MessageModel.created_at < before_created_at,
                    and_(
                        MessageModel.created_at == before_created_at,
                        MessageModel.id < before_id,
                    ),
                ),
            )
            .order_by(MessageModel.created_at.desc(), MessageModel.id.desc())
            .limit(limit)
        )
        with self._sessions() as session:
            models = list(session.scalars(statement).all())
        return [
            Message.model_validate(item, from_attributes=True)
            for item in reversed(models)
        ]
