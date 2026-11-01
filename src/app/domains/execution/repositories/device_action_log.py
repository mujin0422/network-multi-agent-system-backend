"""Repository cho audit command đã gửi xuống thiết bị."""

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import DeviceActionLogModel
from app.domains.execution.schemas import DeviceActionLog


class DeviceActionLogRepository:
    def __init__(self, database_url: str) -> None:
        """Khởi tạo DeviceActionLogRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    def add_all(self, action_logs: list[DeviceActionLog]) -> None:
        """Tạo mới dữ liệu theo nghiệp vụ của phương thức add_all."""
        if not action_logs:
            return
        with self._sessions.begin() as session:
            session.add_all(
                DeviceActionLogModel(**action_log.model_dump())
                for action_log in action_logs
            )

    def get_recent(self, limit: int = 500) -> list[DeviceActionLog]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_recent."""
        statement = (
            select(DeviceActionLogModel)
            .order_by(DeviceActionLogModel.executed_at.desc())
            .limit(limit)
        )
        with self._sessions() as session:
            rows = session.scalars(statement).all()
            return [
                DeviceActionLog.model_validate(row, from_attributes=True)
                for row in rows
            ]
