"""Repository cho audit command đã gửi xuống thiết bị."""

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import DeviceActionLogModel
from app.domains.execution.schemas import DeviceActionLog


class DeviceActionLogRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo DeviceActionLogRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def save_all(self, action_logs: list[DeviceActionLog]) -> None:
        """Lưu nhiều DeviceActionLog vào database."""
        if not action_logs:
            return
        with self._sessions.begin() as session:
            session.add_all(
                DeviceActionLogModel(**action_log.model_dump())
                for action_log in action_logs
            )


    def get_recent(self, limit: int = 500) -> list[DeviceActionLog]:
        """Lấy các DeviceActionLog gần đây nhất, sắp xếp theo executed_at giảm dần."""
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


    def get_all_by_task_id(self, task_id: str) -> list[DeviceActionLog]:
        """Lấy command log của đúng Task, không lấy lẫn log từ Task khác."""
        statement = (
            select(DeviceActionLogModel)
            .where(DeviceActionLogModel.task_id == task_id)
            .order_by(
                DeviceActionLogModel.executed_at,
                DeviceActionLogModel.sequence_number,
                DeviceActionLogModel.id,
            )
        )
        with self._sessions() as session:
            return [
                DeviceActionLog.model_validate(row, from_attributes=True)
                for row in session.scalars(statement).all()
            ]
