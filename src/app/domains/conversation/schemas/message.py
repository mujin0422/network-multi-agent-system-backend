"""Message contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MessageSender(StrEnum):
    """Nguồn gửi message trong conversation."""

    USER = "USER"
    AGENT = "AGENT"


class MessageType(StrEnum):
    """Vai trò của message trong workflow hội thoại."""

    GENERAL = "GENERAL"
    USER_REQUEST = "USER_REQUEST"
    STATUS_UPDATE = "STATUS_UPDATE"
    APPROVAL_REQUEST = "APPROVAL_REQUEST"
    FINAL_RESPONSE = "FINAL_RESPONSE"


class MessageCreate(BaseModel):
    """Payload thêm message vào conversation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sender_by: MessageSender = Field(description="USER hoặc AGENT gửi message.")
    reply_to_message_id: str | None = Field(
        default=None,
        description="ID USER message nguồn khi đây là phản hồi của Agent.",
    )
    message_type: MessageType | None = Field(
        default=None,
        description="Nếu bỏ trống, service suy ra USER_REQUEST hoặc GENERAL.",
    )
    message: str = Field(min_length=1, description="Nội dung message không rỗng.")


class Message(BaseModel):
    """Bản ghi tương ứng bảng ``messages``."""

    id: str = Field(description="Khóa chính của message.")
    conversation_id: str = Field(description="ID conversation chứa message.")
    reply_to_message_id: str | None = Field(
        default=None,
        description="ID message nguồn mà message hiện tại phản hồi.",
    )
    sender_by: MessageSender = Field(description="Nguồn gửi USER hoặc AGENT.")
    message_type: MessageType = Field(
        default=MessageType.GENERAL,
        description="Vai trò của message trong workflow.",
    )
    message: str = Field(description="Nội dung message.")
    created_at: datetime = Field(description="Thời điểm gửi theo UTC.")
