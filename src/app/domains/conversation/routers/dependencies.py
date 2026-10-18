"""Dependency composition for Conversation HTTP routes."""

from functools import lru_cache

from app.core.config import get_settings
from app.domains.conversation import ConversationService
from app.domains.conversation.repositories import (
    PostgresConversationRepository,
)


@lru_cache
def _build_conversation_service() -> ConversationService:
    settings = get_settings()
    repository = PostgresConversationRepository(
        settings.database_url
    )
    return ConversationService(repository)


async def get_conversation_service() -> ConversationService:
    return _build_conversation_service()
