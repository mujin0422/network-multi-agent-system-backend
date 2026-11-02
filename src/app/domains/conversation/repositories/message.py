"""Repository cho bảng messages."""

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.conversation.models import MessageModel
from app.domains.conversation.schemas import Message


class MessageRepository:
    """Đọc và ghi duy nhất bảng messages."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo MessageRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def save(self, message: Message) -> None:
        """Lưu một message mới; bảng messages không có use case update."""

        with self._sessions.begin() as session:
            session.add(MessageModel(**message.model_dump()))


    def get_all_by_conversation_id(self, conversation_id: str) -> list[Message]:
        """Lấy lịch sử message của một conversation theo thứ tự thời gian."""

        statement = (
            select(MessageModel)
            .where(MessageModel.conversation_id == conversation_id)
            # ID là tie-breaker khi hai message có cùng timestamp.
            .order_by(MessageModel.created_at, MessageModel.id)
        )
        with self._sessions() as session:
            models = session.scalars(statement).all()
            return [
                Message.model_validate(item, from_attributes=True)
                for item in models
            ]
