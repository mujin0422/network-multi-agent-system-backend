"""Dependency composition for Conversation HTTP routes."""

from functools import lru_cache

from langchain_nvidia_ai_endpoints import ChatNVIDIA

from app.core.config import get_settings
from app.domains.conversation import ConversationService
from app.domains.conversation.repositories import (
    ConversationRepository,
    MessageRepository,
)
from app.domains.conversation.services import ConversationTitleGenerator


@lru_cache
def _build_conversation_service() -> ConversationService:
    settings = get_settings()
    return ConversationService(
        ConversationRepository(settings.database_url),
        MessageRepository(settings.database_url),
    )


async def get_conversation_service() -> ConversationService:
    return _build_conversation_service()


@lru_cache
def _build_conversation_title_generator() -> ConversationTitleGenerator:
    """Dùng NVIDIA LLM nếu đã cấu hình; nếu chưa có thì generator tự fallback."""

    settings = get_settings()
    chat_model = None
    if settings.nvidia_api_key and settings.nvidia_model:
        chat_model = ChatNVIDIA(
            model=settings.nvidia_model,
            api_key=settings.nvidia_api_key,
            temperature=0,
        )
    return ConversationTitleGenerator(
        chat_model,
        timeout_seconds=settings.conversation_title_timeout_seconds,
    )


async def get_conversation_title_generator() -> ConversationTitleGenerator:
    return _build_conversation_title_generator()
