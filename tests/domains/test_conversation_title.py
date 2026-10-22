"""Unit tests cho title của Conversation đầu tiên."""

import asyncio

from app.domains.conversation.schemas import Conversation, ConversationStart, Message
from app.domains.conversation.services import ConversationService, ConversationTitleGenerator
from app.domains.conversation.utils import (
    fallback_conversation_title,
    normalize_conversation_title,
)


class StubChatModel:
    def __init__(self, content: object = "  **Kiểm tra OSPF trên P1**  ") -> None:
        self.content = content

    async def ainvoke(self, _messages: object) -> object:
        return type("Result", (), {"content": self.content})()


class FailingChatModel:
    async def ainvoke(self, _messages: object) -> object:
        raise RuntimeError("provider unavailable")


class StubConversationRepository:
    def __init__(self) -> None:
        self.conversation: Conversation | None = None
        self.message: Message | None = None

    def create_with_first_message(
        self,
        conversation: Conversation,
        message: Message,
    ) -> None:
        self.conversation = conversation
        self.message = message

    def save_conversation(self, conversation: Conversation) -> None:
        self.conversation = conversation

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        if self.conversation and self.conversation.id == conversation_id:
            return self.conversation
        return None

    def list_conversations(self, user_id: str | None = None) -> list[Conversation]:
        if self.conversation is None:
            return []
        if user_id is not None and self.conversation.user_id != user_id:
            return []
        return [self.conversation]


class StubMessageRepository:
    def save(self, message: Message) -> None:
        raise AssertionError("start() phải dùng transaction repository")

    def list_by_conversation(self, _conversation_id: str) -> list[Message]:
        return []


def test_normalize_title_removes_multiline_and_limits_length() -> None:
    value = "# Kiểm tra routing\ntrên P1 " + "chi tiết " * 30

    title = normalize_conversation_title(value)

    assert "\n" not in title
    assert not title.startswith("#")
    assert len(title) <= 100


def test_title_generator_uses_llm_content() -> None:
    title = asyncio.run(
        ConversationTitleGenerator(StubChatModel()).generate(
            "Kiểm tra trạng thái OSPF trên P1"
        )
    )

    assert title == "Kiểm tra OSPF trên P1"


def test_title_generator_falls_back_when_llm_fails() -> None:
    message = "Kiểm tra routing table trên P1"

    title = asyncio.run(
        ConversationTitleGenerator(FailingChatModel()).generate(message)
    )

    assert title == fallback_conversation_title(message)


def test_start_creates_conversation_and_first_message_together() -> None:
    repository = StubConversationRepository()
    service = ConversationService(repository, StubMessageRepository())

    started = service.start(
        "user-test",
        ConversationStart(message="Kiểm tra routing table trên P1"),
    )

    assert repository.conversation == started.conversation
    assert repository.message == started.message
    assert started.conversation.user_id == "user-test"
    assert started.message.conversation_id == started.conversation.id
    assert started.message.sender_by == "USER"
    assert started.message.message_type == "USER_REQUEST"
