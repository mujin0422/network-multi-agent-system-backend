"""Tiện ích tạo mã định danh theo quy ước trong tài liệu thiết kế."""

from datetime import UTC, datetime
from uuid import uuid4


def generate_id(prefix: str) -> str:
    """Tạo ID dễ đọc, có ngày tạo và phần ngẫu nhiên để tránh trùng."""
    date_part = datetime.now(UTC).strftime("%d%m%y")
    return f"{prefix}-{date_part}-{uuid4().hex[:8]}"
