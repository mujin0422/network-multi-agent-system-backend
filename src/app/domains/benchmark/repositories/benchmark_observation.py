"""Read-only evidence for benchmark timing and agent-to-tool interaction counts."""

from typing import Protocol

from sqlalchemy import func, select

from app.core.database import create_session_factory
from app.domains.benchmark.schemas.benchmark_observation import BenchmarkObservation
from app.domains.conversation.models import MessageModel
from app.domains.execution.models import TaskExecutionModel


class BenchmarkObservationReaderProtocol(Protocol):
    def get_for_task(self, task_id: str, source_message_id: str) -> BenchmarkObservation:
        """Return request timestamp and number of persisted tool calls."""
        ...


class BenchmarkObservationRepository:
    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def get_for_task(self, task_id: str, source_message_id: str) -> BenchmarkObservation:
        with self._sessions() as session:
            request_created_at = session.scalar(
                select(MessageModel.created_at).where(MessageModel.id == source_message_id)
            )
            tool_calls = session.scalar(
                select(func.count(TaskExecutionModel.id)).where(
                    TaskExecutionModel.task_id == task_id,
                    TaskExecutionModel.tool_name.is_not(None),
                )
            )
        return BenchmarkObservation(
            source_message_created_at=request_created_at,
            agent_tool_calls=int(tool_calls) if tool_calls is not None else None,
        )
