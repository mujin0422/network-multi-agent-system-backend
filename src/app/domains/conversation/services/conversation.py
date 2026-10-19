"""Public service cung cấp các use case hội thoại cho API và agent."""

from datetime import UTC, datetime

from app.core.exceptions import ResourceNotFoundError
from app.core.utils import generate_id
from app.domains.conversation.repositories import ConversationRepository
from app.domains.conversation.schemas import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    Message,
    MessageCreate,
)


class ConversationService:
    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    def create(self, payload: ConversationCreate) -> Conversation:
        now = datetime.now(UTC)
        conversation = Conversation(
            id=generate_id("cons"),
            user_id=payload.user_id,
            title=payload.title,
            created_at=now,
            last_updated_at=now,
        )
        self._repository.save_conversation(conversation)
        return conversation

    def list(self, user_id: str | None = None) -> list[Conversation]:
        return self._repository.list_conversations(user_id)

    def get(self, conversation_id: str) -> ConversationDetail:
        conversation = self._require_conversation(conversation_id)
        return ConversationDetail(
            **conversation.model_dump(),
            messages=self._repository.list_messages(conversation_id),
        )

    def list_messages(self, conversation_id: str) -> list[Message]:
        """Lấy danh sách message của một conversation đã tồn tại."""

        self._require_conversation(conversation_id)
        return self._repository.list_messages(conversation_id)

    def add_message(self, conversation_id: str, payload: MessageCreate) -> Message:
        conversation = self._require_conversation(conversation_id)
        now = datetime.now(UTC)
        message = Message(
            id=generate_id("mesg"),
            conversation_id=conversation_id,
            sender_by=payload.sender_by,
            message=payload.message,
            created_at=now,
        )
        self._repository.save_message(message)
        return message

    def _require_conversation(self, conversation_id: str) -> Conversation:
        conversation = self._repository.get_conversation(conversation_id)
        if conversation is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy conversation '{conversation_id}'"
            )
        return conversation
