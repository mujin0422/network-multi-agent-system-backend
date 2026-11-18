"""PostgreSQL LISTEN adapter cho Task activity SSE."""

import json
from types import TracebackType
from typing import Any

from psycopg import AsyncConnection, sql

from app.core.task_events import TASK_ACTIVITY_CHANNEL


class PostgresTaskEventListener:
    """Giữ một LISTEN connection riêng trong vòng đời của một SSE client."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._connection: AsyncConnection | None = None

    async def __aenter__(self) -> "PostgresTaskEventListener":
        self._connection = await AsyncConnection.connect(
            self._database_url,
            autocommit=True,
        )
        await self._connection.execute(
            sql.SQL("LISTEN {}").format(sql.Identifier(TASK_ACTIVITY_CHANNEL))
        )
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def wait(self, timeout_seconds: float) -> dict[str, Any] | None:
        """Chờ tối đa một NOTIFY; timeout trả None để caller phát heartbeat."""

        if self._connection is None:
            raise RuntimeError("Task event listener chưa được mở")
        async for notification in self._connection.notifies(
            timeout=timeout_seconds,
            stop_after=1,
        ):
            try:
                payload = json.loads(notification.payload)
            except (json.JSONDecodeError, TypeError):
                return None
            return payload if isinstance(payload, dict) else None
        return None


__all__ = ["PostgresTaskEventListener"]
