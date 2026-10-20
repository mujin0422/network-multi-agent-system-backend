"""Public service cung cấp các use case hội thoại cho API và agent."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import ResourceNotFoundError
from app.core.utils import IdPrefix, generate_id
from app.domains.conversation.repositories import (
    ConversationRepositoryProtocol,
    MessageRepositoryProtocol,
)
from app.domains.conversation.schemas import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    Message,
    MessageCreate,
)


class ConversationService:
    def __init__(
        self,
        conversation_repository: ConversationRepositoryProtocol,
        message_repository: MessageRepositoryProtocol,
    ) -> None:
        self._conversation_repository = conversation_repository
        self._message_repository = message_repository

    # CREATE (Conversation) — Tạo conversation mới.
    def create(self, payload: ConversationCreate) -> Conversation:
        now = datetime.now(UTC)
        conversation = Conversation(
            id=generate_id(IdPrefix.CONVERSATION),
            user_id=payload.user_id,
            title=payload.title,
            created_at=now,
            last_updated_at=now,
        )
        self._conversation_repository.save_conversation(conversation)
        return conversation

    # READ (Conversation) — Lấy danh sách conversation, có thể lọc theo user_id.
    def list(self, user_id: str | None = None) -> list[Conversation]:
        return self._conversation_repository.list_conversations(user_id)

    # READ (Conversation) — Lấy chi tiết conversation theo mã, bao gồm danh sách message.
    def get(self, conversation_id: str) -> ConversationDetail:
        conversation = self._require_conversation(conversation_id)
        return ConversationDetail(
            **conversation.model_dump(),
            messages=self._message_repository.list_by_conversation(conversation_id),
        )

    # READ (Message) — Lấy danh sách message của một conversation đã tồn tại.
    def list_messages(self, conversation_id: str) -> list[Message]:
        self._require_conversation(conversation_id)
        return self._message_repository.list_by_conversation(conversation_id)

    # CREATE (Message) — Lưu message mới vào conversation đã tồn tại.
    def add_message(self, conversation_id: str, payload: MessageCreate) -> Message:
        conversation = self._require_conversation(conversation_id)
        now = datetime.now(UTC)
        message = Message(
            id=generate_id(IdPrefix.MESSAGE),
            conversation_id=conversation_id,
            sender_by=payload.sender_by,
            message=payload.message,
            created_at=now,
        )
        self._message_repository.save(message)
        return message

    # READ (Conversation) — Xác nhận conversation tồn tại, nếu không ném lỗi ResourceNotFoundError.
    def _require_conversation(self, conversation_id: str) -> Conversation:
        conversation = self._conversation_repository.get_conversation(conversation_id)
        if conversation is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy conversation '{conversation_id}'"
            )
        return conversation
