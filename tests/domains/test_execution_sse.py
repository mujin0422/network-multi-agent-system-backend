"""Kiểm thử wire format của Task SSE."""

import asyncio
import json
from datetime import UTC, datetime
from types import SimpleNamespace

from app.core.task_event_listener import PostgresTaskEventListener
from app.domains.execution.routers.execution import _encode_sse_event
from app.domains.execution.schemas import ActivityEventType, TaskStreamEvent


def test_sse_event_contains_id_type_and_json_payload() -> None:
    event = TaskStreamEvent(
        event_id="7",
        event_type=ActivityEventType.COMMAND_EXECUTED,
        task_id="task-test",
        sequence_number=7,
        occurred_at=datetime.now(UTC),
        data={"id": "actv-test", "event_status": "SUCCESS"},
    )

    encoded = _encode_sse_event(event)

    assert encoded.startswith("id: 7\nevent: task_activity\ndata: {")
    assert '"task_id":"task-test"' in encoded
    assert '"sequence_number":7' in encoded
    assert encoded.endswith("\n\n")


def test_postgres_listener_decodes_notification_payload() -> None:
    listener = PostgresTaskEventListener("postgresql://unused")

    class ConnectionStub:
        async def notifies(self, **_kwargs):
            yield SimpleNamespace(
                payload=json.dumps({"task_id": "task-test", "sequence_number": 8})
            )

    listener._connection = ConnectionStub()

    assert asyncio.run(listener.wait(1)) == {
        "task_id": "task-test",
        "sequence_number": 8,
    }
