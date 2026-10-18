"""Conversation contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.conversation.schemas.message import Message


class ConversationCreate(BaseModel):
    """Payload tạo một phiên hội thoại mới."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(min_length=1, description="ID user sở hữu conversation.")
    title: str = Field(
        min_length=1,
        max_length=255,
        description="Tiêu đề không rỗng của conversation.",
    )


class Conversation(BaseModel):
    """Bản ghi tương ứng bảng ``conversations``."""

    id: str = Field(description="Khóa chính của conversation.")
    user_id: str = Field(description="ID user sở hữu conversation.")
    title: str = Field(max_length=255, description="Tiêu đề conversation.")
    created_at: datetime = Field(description="Thời điểm tạo theo UTC.")
    last_updated_at: datetime = Field(
        description="Thời điểm hoạt động gần nhất, được cập nhật khi có message.",
    )


class ConversationDetail(Conversation):
    messages: list[Message] = Field(
        default_factory=list,
        description="Danh sách message thuộc conversation.",
    )