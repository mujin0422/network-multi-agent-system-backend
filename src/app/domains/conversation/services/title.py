"""Sinh tiêu đề Conversation từ USER_REQUEST đầu tiên."""

import asyncio
from typing import Any, Protocol

from langchain_core.messages import HumanMessage, SystemMessage

from app.domains.conversation.utils import fallback_conversation_title
from app.domains.conversation.utils import normalize_conversation_title


class ConversationTitleGeneratorProtocol(Protocol):
    async def generate(self, first_message: str) -> str: ...


class ConversationTitleGenerator:
    """Gọi LLM khi đã cấu hình và luôn có deterministic fallback."""

    def __init__(self, chat_model: Any | None, timeout_seconds: float = 10.0) -> None:
        self._chat_model = chat_model
        self._timeout_seconds = timeout_seconds

    async def generate(self, first_message: str) -> str:
        fallback = fallback_conversation_title(first_message)
        if self._chat_model is None:
            return fallback

        try:
            result = await asyncio.wait_for(
                self._chat_model.ainvoke(
                    [
                        SystemMessage(
                            content=(
                                "Bạn tạo tiêu đề ngắn cho cuộc hội thoại. Chỉ trả về "
                                "một dòng tiêu đề, tối đa 100 ký tự, cùng ngôn ngữ với "
                                "yêu cầu. Không dùng Markdown, dấu ngoặc kép hoặc giải thích. "
                                "Giữ nguyên hostname, IP, giao thức và thuật ngữ kỹ thuật."
                            )
                        ),
                        HumanMessage(content=first_message),
                    ]
                ),
                timeout=self._timeout_seconds,
            )
        except Exception:
            return fallback

        content = getattr(result, "content", result)
        if not isinstance(content, str):
            return fallback
        return normalize_conversation_title(content)
