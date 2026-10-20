"""Persistence contract và PostgreSQL adapter của Conversation domain."""

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.conversation.models import ConversationModel
from app.domains.conversation.schemas import Conversation


class ConversationRepositoryProtocol(Protocol):
    """Contract persistence của bảng conversations dành cho service."""

    def save_conversation(self, conversation: Conversation) -> None: ...

    def get_conversation(self, conversation_id: str) -> Conversation | None: ...

    def list_conversations(self, user_id: str | None = None) -> list[Conversation]: ...


class ConversationRepository:
    """Repository chỉ quản lý bảng conversations."""

    def __init__(self, database_url: str) -> None:
        # Session factory tạo session mới cho từng thao tác và không giữ kết nối database như state lâu dài bên trong repository.
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


    def get_conversation(self, conversation_id: str) -> Conversation | None:
        """Lấy một conversation; trả None để service quyết định lỗi nghiệp vụ."""

        with self._sessions() as session:
            model = session.get(ConversationModel, conversation_id)
            return Conversation.model_validate(model, from_attributes=True) if model else None


    def list_conversations(self, user_id: str | None = None) -> list[Conversation]:
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
