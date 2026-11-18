"""Public service cung cấp các use case hội thoại cho API và agent."""

from __future__ import annotations

from datetime import UTC, datetime

from app.core.exceptions import ResourceNotFoundError
from app.core.utils import IdPrefix, generate_id
from app.domains.conversation.repositories import (
    ConversationRepository,
    MessageRepository,
)
from app.domains.conversation.schemas import (
    Conversation,
    ConversationDetail,
    ConversationPage,
    ConversationStart,
    ConversationStarted,
    ConversationTitleUpdate,
    Message,
    MessageCreate,
    MessagePage,
    MessageSender,
    MessageType,
)
from app.domains.conversation.utils import (
    DEFAULT_CONVERSATION_TITLE,
    decode_cursor,
    encode_cursor,
    normalize_conversation_title,
)


class ConversationService:
    def __init__(
        self,
        conversation_repository: ConversationRepository,
        message_repository: MessageRepository,
    ) -> None:
        """Khởi tạo ConversationService cùng các phụ thuộc cần thiết."""
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
        if message.conversation_id != conversation.id:
            raise ValueError("Message đầu tiên không thuộc Conversation cần tạo")
        self._conversation_repository.create_with_first_message(
            conversation,
            message,
        )
        return ConversationStarted(conversation=conversation, message=message)

    def update_title(self, conversation: Conversation, title: str) -> Conversation:
        """Lưu title đã chuẩn hóa mà không thay đổi dữ liệu Message đầu tiên."""

        current = self._require_conversation(conversation.id)
        if current.title != DEFAULT_CONVERSATION_TITLE:
            return current
        updated = current.model_copy(
            update={
                "title": normalize_conversation_title(title),
                "last_updated_at": datetime.now(UTC),
            }
        )
        self._conversation_repository.save_conversation(updated)
        return updated

    def rename(
        self,
        conversation_id: str,
        user_id: str,
        payload: ConversationTitleUpdate,
    ) -> Conversation:
        """Đổi tiêu đề nếu conversation thuộc đúng người dùng hiện tại."""

        conversation = self._require_conversation(conversation_id)
        if conversation.user_id != user_id:
            raise ResourceNotFoundError(
                f"Không tìm thấy conversation '{conversation_id}'"
            )
        updated = conversation.model_copy(
            update={
                "title": normalize_conversation_title(payload.title),
                "last_updated_at": datetime.now(UTC),
            }
        )
        self._conversation_repository.save_conversation(updated)
        return updated

    # READ (Conversation) — Lấy danh sách conversation, có thể lọc theo user_id.
    def list(self, user_id: str | None = None) -> list[Conversation]:
        """Lấy danh sách conversation, có thể lọc theo người dùng."""

        return self._conversation_repository.get_all(user_id)

    def list_page(
        self,
        *,
        user_id: str | None,
        limit: int,
        cursor: str | None,
    ) -> ConversationPage:
        """Lấy một trang conversation theo cursor của bản ghi cuối trang trước."""

        before_updated_at, before_id = decode_cursor(cursor)
        items, has_more = self._conversation_repository.get_page(
            user_id=user_id,
            limit=limit,
            before_updated_at=before_updated_at,
            before_id=before_id,
        )
        last = items[-1] if items else None
        return ConversationPage(
            items=items,
            has_more=has_more,
            next_cursor=(
                encode_cursor(last.last_updated_at, last.id)
                if has_more and last is not None
                else None
            ),
        )

    # READ (Conversation) — Lấy chi tiết conversation theo mã, bao gồm danh sách message.
    def get(self, conversation_id: str) -> ConversationDetail:
        """Truy vấn dữ liệu theo phạm vi của phương thức get."""
        conversation = self._require_conversation(conversation_id)
        return ConversationDetail(
            **conversation.model_dump(),
            messages=self._message_repository.get_all_by_conversation_id(
                conversation_id
            ),
        )

    # =============================================================================
    # Message — lấy và lưu tin nhắn trong hội thoại
    # =============================================================================

    # READ (Message) — Lấy danh sách message của một conversation đã tồn tại.
    def list_messages(self, conversation_id: str) -> list[Message]:
        """Truy vấn danh sách dữ liệu theo phạm vi của phương thức list_messages."""
        self._require_conversation(conversation_id)
        return self._message_repository.get_all_by_conversation_id(conversation_id)

    def list_message_page(
        self,
        conversation_id: str,
        *,
        limit: int,
        cursor: str | None,
    ) -> MessagePage:
        """Lấy một trang lịch sử message cũ dần theo cursor."""

        self._require_conversation(conversation_id)
        before_created_at, before_id = decode_cursor(cursor)
        items, has_more = self._message_repository.get_page_by_conversation_id(
            conversation_id,
            limit=limit,
            before_created_at=before_created_at,
            before_id=before_id,
        )
        oldest = items[0] if items else None
        return MessagePage(
            items=items,
            has_more=has_more,
            next_cursor=(
                encode_cursor(oldest.created_at, oldest.id)
                if has_more and oldest is not None
                else None
            ),
        )

    def get_recent_messages_before(
        self,
        message: Message,
        *,
        limit: int,
    ) -> list[Message]:
        """Lấy lịch sử gần nhất trước message nguồn để tạo ngữ cảnh AI."""

        self._require_conversation(message.conversation_id)
        return self._message_repository.get_recent_before(
            message.conversation_id,
            before_created_at=message.created_at,
            before_id=message.id,
            limit=limit,
        )

    # CREATE (Message) — Lưu message mới vào conversation đã tồn tại.
    def create_message(self, conversation_id: str, payload: MessageCreate) -> Message:
        """Tạo message mới trong conversation đã tồn tại."""

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
            structured_data=payload.structured_data,
            created_at=now,
        )
        self._message_repository.save(message)
        return message

    # =============================================================================
    # Xác minh hội thoại
    # =============================================================================

    # READ (Conversation) — Xác nhận conversation tồn tại, nếu không ném lỗi ResourceNotFoundError.
    def _require_conversation(self, conversation_id: str) -> Conversation:
        """Lấy conversation hoặc phát sinh lỗi nếu không tồn tại."""

        conversation = self._conversation_repository.get_by_id(conversation_id)
        if conversation is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy conversation '{conversation_id}'"
            )
        return conversation
