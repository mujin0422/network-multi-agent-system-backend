"""PostgreSQL repository của Conversation domain."""

from datetime import datetime

from sqlalchemy import and_, or_, select

from app.core.database import create_session_factory
from app.domains.conversation.models import ConversationModel, MessageModel
from app.domains.conversation.schemas import Conversation, Message


class ConversationRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo ConversationRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def save_conversation(self, conversation: Conversation) -> None:
        """Tạo mới hoặc cập nhật conversation theo primary key."""
        values = conversation.model_dump()
        with self._sessions.begin() as session:
            model = session.get(ConversationModel, conversation.id)
            if model is None:
                # Schema Pydantic được chuyển thành ORM model tại boundary này.
                session.add(ConversationModel(**values))
                return
            # Chỉ cập nhật các cột thuộc bảng conversations. Message được quản lý riêng bởi MessageRepository.
            model.user_id = conversation.user_id
            model.title = conversation.title
            model.last_updated_at = conversation.last_updated_at


    def create_with_first_message(self, conversation: Conversation, message: Message,) -> None:
        """Tạo Conversation và USER_REQUEST đầu tiên trong cùng transaction."""
        with self._sessions.begin() as session:
            session.add(ConversationModel(**conversation.model_dump()))
            session.add(MessageModel(**message.model_dump()))


    def get_by_id(self, conversation_id: str) -> Conversation | None:
        """Lấy một conversation; trả None để service quyết định lỗi nghiệp vụ."""
        with self._sessions() as session:
            model = session.get(ConversationModel, conversation_id)
            return Conversation.model_validate(model, from_attributes=True) if model else None


    def get_all(self, user_id: str | None = None) -> list[Conversation]:
        """Lấy toàn bộ conversation hoặc chỉ conversation của một user."""
        statement = select(ConversationModel)
        if user_id is not None:
            statement = statement.where(ConversationModel.user_id == user_id)
        # Hội thoại hoạt động gần nhất xuất hiện trước trên giao diện chat.
        statement = statement.order_by(
            ConversationModel.last_updated_at.desc(),
            ConversationModel.id,
        )
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [
                Conversation.model_validate(item, from_attributes=True)
                for item in models
            ]

    def get_page(
        self,
        *,
        user_id: str | None,
        limit: int,
        before_updated_at: datetime | None = None,
        before_id: str | None = None,
    ) -> tuple[list[Conversation], bool]:
        """Lấy một trang conversation mới nhất bằng keyset pagination."""

        statement = select(ConversationModel)
        if user_id is not None:
            statement = statement.where(ConversationModel.user_id == user_id)
        if before_updated_at is not None and before_id is not None:
            statement = statement.where(
                or_(
                    ConversationModel.last_updated_at < before_updated_at,
                    and_(
                        ConversationModel.last_updated_at == before_updated_at,
                        ConversationModel.id < before_id,
                    ),
                )
            )
        statement = statement.order_by(
            ConversationModel.last_updated_at.desc(),
            ConversationModel.id.desc(),
        ).limit(limit + 1)
        with self._sessions() as session:
            models = list(session.scalars(statement).all())
        has_more = len(models) > limit
        return (
            [
                Conversation.model_validate(item, from_attributes=True)
                for item in models[:limit]
            ],
            has_more,
        )
