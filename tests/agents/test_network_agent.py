"""Unit tests cho Network Agent execution worker."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.agents.network import NetworkAgent, NetworkExecutionStatus
from app.domains.execution.schemas import (
    AccessMode,
    DeviceRole,
    Operation,
    OperationDeviceStatus,
    OperationStatus,
    TaskOperationDevice,
)
from app.tools import CommandResult


class StubNetworkTool:
    def __init__(self) -> None:
        self.calls = []

    def execute(self, device_id, access_mode, commands):
        self.calls.append((device_id, access_mode, commands))
        return [CommandResult(command=commands[0], output="10.0.0.0/24")]


def test_network_agent_executes_operation_for_planned_device(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_immediately(function, *args):
        return function(*args)

    monkeypatch.setattr(asyncio, "to_thread", run_immediately)
    now = datetime.now(UTC)
    operation = Operation(
        id="oper-1",
        task_id="task-1",
        operation_intent="GET_ROUTING_TABLE",
        display_order=1,
        operation_status=OperationStatus.PENDING,
        operation_parameters={"command": "show ip route"},
        created_at=now,
    )
    mapping = TaskOperationDevice(
        id="oper-devv-1",
        operation_id=operation.id,
        device_id="devc-1",
        operation_device_status=OperationDeviceStatus.PENDING,
        device_role=DeviceRole.SOURCE,
        access_mode=AccessMode.READ,
    )
    tool = StubNetworkTool()

    result = asyncio.run(NetworkAgent(tool).execute(operation, mapping))

    assert result.status == NetworkExecutionStatus.SUCCESS
    assert result.results[0].output == "10.0.0.0/24"
    assert tool.calls == [("devc-1", AccessMode.READ, ["show ip route"])]


def test_network_agent_returns_failed_result_when_tool_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run_immediately(function, *args):
        return function(*args)

    monkeypatch.setattr(asyncio, "to_thread", run_immediately)
    class FailingTool:
        def execute(self, device_id, access_mode, commands):
            raise ConnectionError("Không thể đăng nhập")

    now = datetime.now(UTC)
    operation = Operation(
        id="oper-1",
        task_id="task-1",
        operation_intent="CONFIGURE_OSPF",
        display_order=1,
        operation_status=OperationStatus.PENDING,
        operation_parameters={"commands": ["router ospf 1"]},
        created_at=now,
    )
    mapping = TaskOperationDevice(
        id="oper-devv-1",
        operation_id=operation.id,
        device_id="devc-1",
        operation_device_status=OperationDeviceStatus.PENDING,
        device_role=DeviceRole.TARGET,
        access_mode=AccessMode.WRITE,
    )

    result = asyncio.run(NetworkAgent(FailingTool()).execute(operation, mapping))

    assert result.status == NetworkExecutionStatus.FAILED
    assert result.error_message == "Không thể đăng nhập"
