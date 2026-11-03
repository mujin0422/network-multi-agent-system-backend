"""Read-only benchmark evidence: logged tool calls and approval pauses."""

from typing import Protocol

from sqlalchemy import func, select

from app.core.database import create_session_factory
from app.domains.benchmark.schemas.benchmark_observation import (
    ApprovalWaitInterval,
    BenchmarkObservation,
)
from app.domains.conversation.models import MessageModel
from app.domains.execution.models import TaskActivityEventModel, TaskExecutionModel
from app.domains.execution.schemas import ActivityEventType


class BenchmarkObservationReaderProtocol(Protocol):
    def get_for_task(self, task_id: str, source_message_id: str) -> BenchmarkObservation:
        """Return timing evidence and agent-to-tool call count."""
        ...


def approval_pauses_from_events(
    events: list[tuple[ActivityEventType, object]],
) -> tuple[list[ApprovalWaitInterval], bool]:
    """Pair REQUESTED -> next EXECUTION_STARTED, not approval decision alone.

    Resume may happen after the user approves. Waiting ends when orchestration
    actually runs again. Unmatched or repeated pauses are marked incomplete.
    """
    start = None
    pauses: list[ApprovalWaitInterval] = []
    invalid = False
    for event_type, when in events:
        if event_type == ActivityEventType.APPROVAL_REQUESTED:
            if start is not None:
                invalid = True
            start = when
        elif event_type == ActivityEventType.EXECUTION_STARTED and start is not None:
            pauses.append(ApprovalWaitInterval(started_at=start, resumed_at=when))
            start = None
    return pauses, invalid or start is not None


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
            events = session.execute(
                select(
                    TaskActivityEventModel.event_type,
                    TaskActivityEventModel.created_at,
                )
                .where(
                    TaskActivityEventModel.task_id == task_id,
                    TaskActivityEventModel.event_type.in_([
                        ActivityEventType.APPROVAL_REQUESTED,
                        ActivityEventType.EXECUTION_STARTED,
                    ]),
                )
                .order_by(
                    TaskActivityEventModel.sequence_number,
                    TaskActivityEventModel.id,
                )
            ).all()
        pauses, open_wait = approval_pauses_from_events(list(events))
        return BenchmarkObservation(
            source_message_created_at=request_created_at,
            agent_tool_calls=int(tool_calls) if tool_calls is not None else None,
            approval_wait_intervals=pauses,
            approval_wait_open=open_wait,
        )
