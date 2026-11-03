"""Shutdown waits for the database sweep instead of cancelling a thread."""

import asyncio
from types import SimpleNamespace

from app.core.approval_timeout_worker import run_approval_timeout_worker


def test_approval_worker_can_stop_without_waiting_for_poll_interval(monkeypatch):
    calls = []

    class FakeRepo:
        def __init__(self, database_url):
            assert database_url == "sqlite:///:memory:"

        def expire_due_approvals(self, now, timeout_minutes):
            calls.append((now, timeout_minutes))
            return []

    monkeypatch.setattr(
        "app.core.approval_timeout_worker.ApprovalTimeoutRepository", FakeRepo
    )

    async def check():
        event = asyncio.Event()
        settings = SimpleNamespace(
            database_url="sqlite:///:memory:",
            approval_timeout_minutes=15,
            approval_sweep_interval_seconds=3600,
        )
        worker = asyncio.create_task(run_approval_timeout_worker(settings, event))
        # Let the first sweep run, then wake the long sleep by setting the flag.
        while not calls:
            await asyncio.sleep(0.01)
        event.set()
        await asyncio.wait_for(worker, timeout=2.0)

    asyncio.run(check())
    assert len(calls) == 1
    assert calls[0][1] == 15
