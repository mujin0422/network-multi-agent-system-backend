"""Repository cho timeline trong bảng task_activity_events."""

import json

from sqlalchemy import func, select, text

from app.core.database import create_session_factory
from app.core.task_events import TASK_ACTIVITY_CHANNEL
from app.domains.execution.models import TaskActivityEventModel
from app.domains.execution.schemas import TaskActivityEvent


class TaskActivityEventRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo TaskActivityEventRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def get_all_by_task_id(self, task_id: str) -> list[TaskActivityEvent]:
        """Lấy timeline của Task theo sequence_number ổn định."""
        statement = (
            select(TaskActivityEventModel)
            .where(TaskActivityEventModel.task_id == task_id)
            .order_by(
                TaskActivityEventModel.sequence_number,
                TaskActivityEventModel.id,
            )
        )
        with self._sessions() as session:
            return [
                TaskActivityEvent.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]


    def get_all_after_sequence(
        self,
        task_id: str,
        sequence_number: int,
        limit: int = 100,
    ) -> list[TaskActivityEvent]:
        """Lấy phần timeline mới hơn sequence client đã nhận."""

        statement = (
            select(TaskActivityEventModel)
            .where(
                TaskActivityEventModel.task_id == task_id,
                TaskActivityEventModel.sequence_number > sequence_number,
            )
            .order_by(
                TaskActivityEventModel.sequence_number,
                TaskActivityEventModel.id,
            )
            .limit(limit)
        )
        with self._sessions() as session:
            return [
                TaskActivityEvent.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]

        
    def save_task_activity_event(self, event: TaskActivityEvent) -> None:
        """Tạo hoặc cập nhật một mốc timeline."""
        with self._sessions.begin() as session:
            model = session.get(TaskActivityEventModel, event.id)
            if model is None:
                session.add(TaskActivityEventModel(**event.model_dump()))
                return
            for field, value in event.model_dump().items():
                setattr(model, field, value)

    def append_task_activity_event(
        self,
        event: TaskActivityEvent,
    ) -> TaskActivityEvent:
        """Cấp sequence, insert và phát NOTIFY trong cùng transaction.

        Advisory lock theo ``task_id`` tuần tự hóa các writer của cùng một Task,
        nhưng vẫn cho phép các Task khác ghi activity song song.
        """

        with self._sessions.begin() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(hashtext(:task_id))"),
                {"task_id": event.task_id},
            )
            next_sequence = int(
                session.scalar(
                    select(
                        func.coalesce(
                            func.max(TaskActivityEventModel.sequence_number),
                            0,
                        )
                        + 1
                    ).where(TaskActivityEventModel.task_id == event.task_id)
                )
                or 1
            )
            persisted = event.model_copy(
                update={"sequence_number": next_sequence}
            )
            session.add(TaskActivityEventModel(**persisted.model_dump()))
            session.flush()
            session.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {
                    "channel": TASK_ACTIVITY_CHANNEL,
                    "payload": json.dumps(
                        {
                            "task_id": persisted.task_id,
                            "sequence_number": persisted.sequence_number,
                        },
                        separators=(",", ":"),
                    ),
                },
            )
            return persisted

