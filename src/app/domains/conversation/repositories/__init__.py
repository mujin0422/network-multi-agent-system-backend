"""Persistence ports and adapters for the Conversation domain."""

from app.domains.conversation.repositories.conversation import (
    ConversationRepository,
    InMemoryConversationRepository,
)

__all__ = ["ConversationRepository", "InMemoryConversationRepository"]
