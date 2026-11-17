"""Chuẩn hóa lỗi Network Agent thành mã ổn định cho UI và log."""

from enum import StrEnum


class NetworkErrorCode(StrEnum):
    """Nhóm lỗi có thể dùng ổn định giữa backend, UI và benchmark."""

    DEVICE_NOT_FOUND = "DEVICE_NOT_FOUND"
    DEVICE_UNREACHABLE = "DEVICE_UNREACHABLE"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    UNKNOWN_NETWORK_ERROR = "UNKNOWN_NETWORK_ERROR"


def classify_network_error(message: str | None) -> NetworkErrorCode | None:
    """Phân loại exception đã được che secret theo nội dung ổn định."""

    if not message:
        return None
    normalized = message.casefold()
    if "không tìm thấy thiết bị" in normalized or "device not found" in normalized:
        return NetworkErrorCode.DEVICE_NOT_FOUND
    if any(
        marker in normalized
        for marker in (
            "network is unreachable",
            "no route to host",
            "connection refused",
            "host is unreachable",
        )
    ):
        return NetworkErrorCode.DEVICE_UNREACHABLE
    if any(
        marker in normalized
        for marker in ("timed out", "timeout", "không phản hồi trong")
    ):
        return NetworkErrorCode.CONNECTION_TIMEOUT
    if any(
        marker in normalized
        for marker in (
            "authentication failed",
            "không thể đăng nhập",
            "permission denied",
            "login failed",
        )
    ):
        return NetworkErrorCode.AUTHENTICATION_FAILED
    if any(
        marker in normalized
        for marker in ("invalid input", "ambiguous command", "incomplete command")
    ):
        return NetworkErrorCode.COMMAND_REJECTED
    return NetworkErrorCode.UNKNOWN_NETWORK_ERROR
