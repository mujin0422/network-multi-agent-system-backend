"""Persistence contract và bản in-memory của Conversation domain."""

from typing import Protocol
import psycopg
from psycopg.rows import dict_row
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
        self._database_url = database_url

    def _connect(self):
        return psycopg.connect(
            self._database_url,
            row_factory=dict_row
        )

    def save_conversation(self, conversation: Conversation) -> None:
        query = """
            INSERT INTO conversations (
                id, user_id, title, created_at, last_updated_at
            )
            VALUES (
                %(id)s, %(user_id)s, %(title)s,
                %(created_at)s, %(last_updated_at)s
            )
            ON CONFLICT (id) DO UPDATE SET
                user_id = EXCLUDED.user_id,
                title = EXCLUDED.title,
                last_updated_at = EXCLUDED.last_updated_at

        """

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, conversation.model_dump())

    def get_conversation(self, conversation_id: str) -> Conversation | None:
        query = """
            SELECT id, user_id, title, created_at, last_updated_at
            FROM conversations
            WHERE id = %s
        """

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (conversation_id,))
                row = cursor.fetchone()
        return Conversation.model_validate(row) if row else None

    def list_conversations(self, user_id: str | None = None) -> list[Conversation]:
        query = """
            SELECT id, user_id, title, created_at, last_updated_at
            FROM conversations
        """

        params: tuple = ()

        if user_id is not None:
            query += " WHERE user_id = %s"
            params = (user_id,)

        query += " ORDER BY last_updated_at DESC, id "

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

        return [Conversation.model_validate(row) for row in rows]

    def save_message(self, message: Message) -> None:
        query = """
            INSERT INTO messages (
                id, conversation_id, sender_by, message, created_at
            )
            VALUES (
                %(id)s, %(conversation_id)s, %(sender_by)s::message_sender,
                %(message)s, %(created_at)s
            )
        """

        data = message.model_dump()
        sender = data["sender_by"]

        data["sender_by"] = (
            sender.value if hasattr(sender, "value") else sender
        )

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, data)

    def list_messages(self, conversation_id: str) -> list[Message]:
        query = """
            SELECT id, conversation_id, sender_by, message, created_at
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at, id
        """

        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (conversation_id,))
                rows = cursor.fetchall()

        return [Message.model_validate(row) for row in rows]