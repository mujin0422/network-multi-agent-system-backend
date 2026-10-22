"""Tiện ích tạo mã định danh theo quy ước trong tài liệu thiết kế."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4


class IdPrefix(StrEnum):
    """Prefix của các khóa nghiệp vụ VARCHAR(64) trong database design."""

    ROLE = "role"
    MANAGEMENT_FUNCTION = "func"
    ACTION = "acts"
    PERMISSION = "perm"
    USER = "user"
    BRAND = "brnd"
    CATEGORY = "catg"
    CREDENTIAL = "cred"
    DEVICE = "devc"
    CONVERSATION = "cons"
    MESSAGE = "mesg"
    TASK = "task"
    OPERATION = "oper"
    OPERATION_DEPENDENCY = "opdp"
    OPERATION_DEVICE = "oper-devv"
    TASK_EXECUTION = "exec"
    TASK_ACTIVITY = "task-acti"
    OPERATION_DEVICE_APPROVAL = "aprv-devs"


def generate_id(prefix: IdPrefix) -> str:
    """Tạo ID runtime dạng ``prefix-DDMMYY-xxxxxxxx`` và nhỏ hơn 64 ký tự.

    Seed dùng số thứ tự tám ký tự như ``user-221026-00000001``. Runtime dùng tám ký
    tự hexadecimal ngẫu nhiên để tránh phụ thuộc bộ đếm database nhưng vẫn giữ
    đúng prefix và ngày UTC của tài liệu.
    """

    date_part = datetime.now(UTC).strftime("%d%m%y")
    identifier = f"{prefix.value}-{date_part}-{uuid4().hex[:8]}"
    if len(identifier) > 64:
        raise ValueError("ID nghiệp vụ vượt quá giới hạn VARCHAR(64)")
    return identifier


def generate_uuid() -> UUID:
    """Tạo UUIDv4 cho session và các bảng audit/evaluation dùng UUID."""

    return uuid4()
