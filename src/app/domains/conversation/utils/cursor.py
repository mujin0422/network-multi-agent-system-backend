"""Mã hóa cursor phân trang không để lộ cấu trúc query cho client."""

from base64 import urlsafe_b64decode, urlsafe_b64encode
from binascii import Error as Base64Error
from datetime import datetime
import json


def encode_cursor(timestamp: datetime, record_id: str) -> str:
    """Tạo cursor URL-safe từ timestamp và khóa phụ ổn định."""

    payload = json.dumps(
        {"timestamp": timestamp.isoformat(), "id": record_id},
        separators=(",", ":"),
    ).encode()
    return urlsafe_b64encode(payload).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> tuple[datetime | None, str | None]:
    """Giải mã cursor; cursor sai được xem là yêu cầu không hợp lệ."""

    if cursor is None:
        return None, None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(urlsafe_b64decode(padded).decode())
        return datetime.fromisoformat(payload["timestamp"]), str(payload["id"])
    except (
        Base64Error,
        KeyError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise ValueError("Cursor phân trang không hợp lệ") from exc
