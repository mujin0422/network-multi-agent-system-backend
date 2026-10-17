"""Message contracts."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MessageSender(StrEnum):
    """Nguồn gửi message trong conversation."""

    USER = "USER"
    AGENT = "AGENT"


class MessageCreate(BaseModel):
    """Payload thêm message vào conversation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sender_by: MessageSender = Field(description="USER hoặc AGENT gửi message.")
    message: str = Field(min_length=1, description="Nội dung message không rỗng.")


class Message(BaseModel):
    """Bản ghi tương ứng bảng ``messages``."""

    id: str = Field(description="Khóa chính của message.")
    conversation_id: str = Field(description="ID conversation chứa message.")
    sender_by: MessageSender = Field(description="Nguồn gửi USER hoặc AGENT.")
    message: str = Field(description="Nội dung message.")
    created_at: datetime = Field(description="Thời điểm gửi theo UTC.")
