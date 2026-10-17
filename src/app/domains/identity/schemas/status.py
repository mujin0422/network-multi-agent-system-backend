"""Enum contracts owned by the Identity domain."""

from enum import StrEnum


class UserStatus(StrEnum):
    """Trạng thái cho phép hoặc vô hiệu hóa tài khoản."""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
