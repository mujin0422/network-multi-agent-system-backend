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
    ConversationDetail,
    ConversationStart,
    ConversationStarted,
    Message,
    MessageCreate,
    MessageSender,
    MessageType,
)
from app.domains.conversation.utils import DEFAULT_CONVERSATION_TITLE


class ConversationService:
    def __init__(
        self,
        conversation_repository: ConversationRepositoryProtocol,
        message_repository: MessageRepositoryProtocol,
    ) -> None:
        self._conversation_repository = conversation_repository
        self._message_repository = message_repository

    # =============================================================================
    # Conversation — tạo, cập nhật và lấy hội thoại
    # =============================================================================

    def start(
        self,
        user_id: str,
        payload: ConversationStart,
    ) -> ConversationStarted:
        """Tạo Conversation và USER_REQUEST đầu tiên một cách nguyên tử."""

        now = datetime.now(UTC)
        conversation = Conversation(
            id=generate_id(IdPrefix.CONVERSATION),
            user_id=user_id,
            title=DEFAULT_CONVERSATION_TITLE,
            created_at=now,
            last_updated_at=now,
        )
        message = Message(
            id=generate_id(IdPrefix.MESSAGE),
            conversation_id=conversation.id,
            reply_to_message_id=None,
            sender_by=MessageSender.USER,
            message_type=MessageType.USER_REQUEST,
            message=payload.message,
            created_at=now,
        )
        self._conversation_repository.create_with_first_message(
            conversation,
            message,
        )
        return ConversationStarted(conversation=conversation, message=message)

    def update_title(self, conversation: Conversation, title: str) -> Conversation:
        """Lưu title đã chuẩn hóa mà không thay đổi dữ liệu Message đầu tiên."""

        updated = conversation.model_copy(
            update={
                "title": title,
                "last_updated_at": datetime.now(UTC),
            }
        )
        self._conversation_repository.save_conversation(updated)
        return updated

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

    # =============================================================================
    # Message — lấy và lưu tin nhắn trong hội thoại
    # =============================================================================

    # READ (Message) — Lấy danh sách message của một conversation đã tồn tại.
    def list_messages(self, conversation_id: str) -> list[Message]:
        self._require_conversation(conversation_id)
        return self._message_repository.list_by_conversation(conversation_id)

    # CREATE (Message) — Lưu message mới vào conversation đã tồn tại.
    def add_message(self, conversation_id: str, payload: MessageCreate) -> Message:
        self._require_conversation(conversation_id)
        now = datetime.now(UTC)
        message = Message(
            id=generate_id(IdPrefix.MESSAGE),
            conversation_id=conversation_id,
            reply_to_message_id=payload.reply_to_message_id,
            sender_by=payload.sender_by,
            message_type=payload.message_type
            or (
                MessageType.USER_REQUEST
                if payload.sender_by == MessageSender.USER
                else MessageType.GENERAL
            ),
            message=payload.message,
            created_at=now,
        )
        self._message_repository.save(message)
        return message

    # =============================================================================
    # Xác minh hội thoại
    # =============================================================================

    # READ (Conversation) — Xác nhận conversation tồn tại, nếu không ném lỗi ResourceNotFoundError.
    def _require_conversation(self, conversation_id: str) -> Conversation:
        conversation = self._conversation_repository.get_conversation(conversation_id)
        if conversation is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy conversation '{conversation_id}'"
            )
        return conversation
