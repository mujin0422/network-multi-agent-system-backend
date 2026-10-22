"""Chuẩn hóa title hội thoại do LLM hoặc fallback tạo ra."""

import re


DEFAULT_CONVERSATION_TITLE = "Cuộc hội thoại mới"
MAX_CONVERSATION_TITLE_LENGTH = 100


def normalize_conversation_title(value: str) -> str:
    """Đưa title về một dòng, bỏ Markdown/quote và giới hạn 100 ký tự."""

    normalized = re.sub(r"\s+", " ", value).strip()
    normalized = re.sub(r"^(?:[-*#]+\s*)+", "", normalized).strip()
    normalized = normalized.strip("\"'`“”‘’ ")
    normalized = normalized.strip("*_# ")
    if not normalized:
        return DEFAULT_CONVERSATION_TITLE
    if len(normalized) <= MAX_CONVERSATION_TITLE_LENGTH:
        return normalized

    shortened = normalized[:MAX_CONVERSATION_TITLE_LENGTH].rstrip()
    if " " in shortened:
        word_boundary = shortened.rsplit(" ", 1)[0].rstrip()
        if word_boundary:
            shortened = word_boundary
    return shortened or DEFAULT_CONVERSATION_TITLE


def fallback_conversation_title(first_message: str) -> str:
    """Tạo title xác định được khi LLM thiếu cấu hình, lỗi hoặc timeout."""

    return normalize_conversation_title(first_message)
