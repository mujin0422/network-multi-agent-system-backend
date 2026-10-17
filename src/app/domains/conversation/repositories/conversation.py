"""Persistence contract và bản in-memory của Conversation domain."""

from typing import Protocol

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
