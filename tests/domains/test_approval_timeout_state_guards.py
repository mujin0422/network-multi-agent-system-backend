"""Stale workflow callbacks must not rewrite terminal records after expiry."""

from contextlib import contextmanager
from datetime import UTC, datetime
from types import SimpleNamespace

from app.domains.execution.repositories.operation import OperationRepository
from app.domains.execution.repositories.operation_device import OperationDeviceRepository
from app.domains.execution.repositories.task import TaskRepository
from app.domains.execution.schemas import (
    AccessMode,
    DeviceRole,
    Operation,
    OperationDeviceStatus,
    OperationStatus,
    Task,
    TaskOperationDevice,
    TaskStatus,
)


class FakeSession:
    def __init__(self, row):
        self.row = row

    def get(self, _model, _pk, *, with_for_update=False):
        assert with_for_update is True
        return self.row


class FakeSessions:
    def __init__(self, row):
        self.session = FakeSession(row)

    @contextmanager
    def begin(self):
        yield self.session


def test_delayed_callback_cannot_revive_timed_out_task():
    now = datetime.now(UTC)
    stored = SimpleNamespace(task_status=TaskStatus.FAILED, completed_at=now)
    session = FakeSession(stored)
    incoming = Task(
        id="task-1",
        conversation_id="cons-1",
        source_message_id="mesg-1",
        user_id="user-1",
        input_message="configure",
        task_status=TaskStatus.SUCCESS,
        created_at=now,
    )

    TaskRepository.save_in_session(session, incoming)

    assert stored.task_status == TaskStatus.FAILED
    assert stored.completed_at == now


def test_delayed_callback_cannot_override_expired_operation():
    now = datetime.now(UTC)
    stored = SimpleNamespace(operation_status=OperationStatus.REJECTED, completed_at=now)
    repo = object.__new__(OperationRepository)
    repo._sessions = FakeSessions(stored)
    incoming = Operation(
        id="oper-1",
        task_id="task-1",
        display_order=1,
        operation_intent="CONFIGURE",
        operation_status=OperationStatus.SUCCESS,
        operation_parameters={},
        created_at=now,
    )

    repo.save_operation(incoming)

    assert stored.operation_status == OperationStatus.REJECTED
    assert stored.completed_at == now


def test_delayed_callback_cannot_override_expired_device_mapping():
    now = datetime.now(UTC)
    stored = SimpleNamespace(
        operation_device_status=OperationDeviceStatus.REJECTED,
        completed_at=now,
    )
    repo = object.__new__(OperationDeviceRepository)
    repo._sessions = FakeSessions(stored)
    incoming = TaskOperationDevice(
        id="opdv-1",
        operation_id="oper-1",
        device_id="devc-1",
        device_role=DeviceRole.TARGET,
        access_mode=AccessMode.WRITE,
        operation_device_status=OperationDeviceStatus.SUCCESS,
    )

    repo.save_operation_device(incoming)

    assert stored.operation_device_status == OperationDeviceStatus.REJECTED
    assert stored.completed_at == now
