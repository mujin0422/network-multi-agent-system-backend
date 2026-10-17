"""Dependency composition for Conversation HTTP routes."""

from functools import lru_cache

from app.domains.conversation import (
    ConversationService,
    InMemoryConversationRepository,
)


@lru_cache
def _build_conversation_service() -> ConversationService:
    return ConversationService(InMemoryConversationRepository())


async def get_conversation_service() -> ConversationService:
    return _build_conversation_service()
