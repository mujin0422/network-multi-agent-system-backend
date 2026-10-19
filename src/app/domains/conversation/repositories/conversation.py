"""Persistence contract và bản in-memory của Conversation domain."""

from typing import Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.conversation.models import ConversationModel, MessageModel
from app.domains.conversation.schemas import Conversation, Message


class ConversationRepository(Protocol):
    """Port để service không phụ thuộc trực tiếp vào loại database."""

    def save_conversation(self, conversation: Conversation) -> None: ...

    def get_conversation(self, conversation_id: str) -> Conversation | None: ...

    def list_conversations(self, user_id: str | None = None) -> list[Conversation]: ...

    def save_message(self, message: Message) -> None: ...

    def list_messages(self, conversation_id: str) -> list[Message]: ...


class InMemoryConversationRepository:
    """Adapter tạm thời để test API trước khi thay bằng repository SQL."""

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[Message]] = {}

    def save_conversation(self, conversation: Conversation) -> None:
        self._conversations[conversation.id] = conversation.model_copy(deep=True)

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        conversation = self._conversations.get(conversation_id)
        return conversation.model_copy(deep=True) if conversation else None

    def list_conversations(self, user_id: str | None = None) -> list[Conversation]:
        conversations = self._conversations.values()
        if user_id is not None:
            conversations = (item for item in conversations if item.user_id == user_id)
        return [item.model_copy(deep=True) for item in conversations]

    def save_message(self, message: Message) -> None:
        self._messages.setdefault(message.conversation_id, []).append(
            message.model_copy(deep=True)
        )

    def list_messages(self, conversation_id: str) -> list[Message]:
        return [
            item.model_copy(deep=True)
            for item in self._messages.get(conversation_id, [])
        ]

class PostgresConversationRepository:
    """Repository PostgreSQL cho conversations và messages."""

    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def save_conversation(self, conversation: Conversation) -> None:
        values = conversation.model_dump()
        with self._sessions.begin() as session:
            model = session.get(ConversationModel, conversation.id)
            if model is None:
                session.add(ConversationModel(**values))
                return
            model.user_id = conversation.user_id
            model.title = conversation.title
            model.last_updated_at = conversation.last_updated_at

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        with self._sessions() as session:
            model = session.get(ConversationModel, conversation_id)
            return Conversation.model_validate(model, from_attributes=True) if model else None

    def list_conversations(self, user_id: str | None = None) -> list[Conversation]:
        statement = select(ConversationModel)
        if user_id is not None:
            statement = statement.where(ConversationModel.user_id == user_id)
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

    def save_message(self, message: Message) -> None:
        with self._sessions.begin() as session:
            session.add(MessageModel(**message.model_dump()))

    def list_messages(self, conversation_id: str) -> list[Message]:
        statement = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            .order_by(MessageModel.created_at, MessageModel.id)
        )
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [Message.model_validate(item, from_attributes=True) for item in models]
