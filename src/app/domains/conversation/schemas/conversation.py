"""Conversation contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domains.conversation.schemas.message import Message


class ConversationStart(BaseModel):
    """Payload gửi USER_REQUEST đầu tiên và khởi tạo conversation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(
        min_length=1,
        description="Nội dung USER_REQUEST đầu tiên của conversation mới.",
    )


class Conversation(BaseModel):
    """Bản ghi tương ứng bảng ``conversations``."""

    id: str = Field(description="Khóa chính của conversation.")
    user_id: str = Field(description="ID user sở hữu conversation.")
    title: str = Field(max_length=100, description="Tiêu đề conversation.")
    created_at: datetime = Field(description="Thời điểm tạo theo UTC.")
    last_updated_at: datetime = Field(
        description="Thời điểm hoạt động gần nhất, được cập nhật khi có message.",
    )


class ConversationDetail(Conversation):
    messages: list[Message] = Field(
        default_factory=list,
        description="Danh sách message thuộc conversation.",
    )


class ConversationStarted(BaseModel):
    """Kết quả tạo Conversation cùng Message đầu tiên."""

    conversation: Conversation = Field(description="Conversation vừa được tạo.")
    message: Message = Field(description="USER_REQUEST đầu tiên đã được lưu.")
