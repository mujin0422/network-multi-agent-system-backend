"""Repository cho audit command đã gửi xuống thiết bị."""

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import DeviceActionLogModel
from app.domains.execution.schemas import DeviceActionLog


class DeviceActionLogRepository:
    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def add_all(self, action_logs: list[DeviceActionLog]) -> None:
        if not action_logs:
            return
        with self._sessions.begin() as session:
            session.add_all(
                DeviceActionLogModel(**action_log.model_dump())
                for action_log in action_logs
            )

    def list_recent(self, limit: int = 500) -> list[DeviceActionLog]:
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
