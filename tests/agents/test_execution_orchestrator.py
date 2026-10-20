"""Kiểm thử luồng Task -> Operation -> Network Agent."""

import asyncio
from datetime import UTC, datetime

from app.agents.network import NetworkExecutionResult, NetworkExecutionStatus
from app.agents.orchestrator import ExecutionOrchestrator
from app.domains.execution.schemas import (
    AccessMode,
    DependencyType,
    DeviceRole,
    Operation,
    OperationDependency,
    OperationDeviceStatus,
    OperationStatus,
    TaskDetail,
    TaskStatus,
    TaskType,
    TaskOperationDevice,
)


class StubExecutionService:
    def __init__(
        self,
        operations: list[Operation],
        dependencies: list[OperationDependency] | None = None,
    ) -> None:
        self.operations = {operation.id: operation for operation in operations}
        self.dependencies = dependencies or []
        self.tasks = []
        self.mappings = {
            operation.id: TaskOperationDevice(
                id=f"map-{operation.id}",
                operation_id=operation.id,
                device_id="devc-1",
                operation_device_status=OperationDeviceStatus.PENDING,
                device_role=DeviceRole.SOURCE,
                access_mode=AccessMode.READ,
            )
            for operation in operations
        }
        self.executions = []
        self.logs = []

    def get_operation(self, operation_id: str) -> Operation:
        return self.operations[operation_id]

    def list_operation_devices(self, operation_id: str) -> list:
        return [self.mappings[operation_id]]

    def list_dependencies(self, operation_id: str) -> list[OperationDependency]:
        return [item for item in self.dependencies if item.operation_id == operation_id]

    def update_task(self, task) -> None:
        self.tasks.append(task)

    def update_operation(self, operation) -> None:
        self.operations[operation.id] = operation

    def update_operation_device(self, mapping) -> None:
        self.mappings[mapping.operation_id] = mapping

    def save_task_execution(self, execution) -> None:
        self.executions.append(execution)

    def save_device_action_logs(self, logs) -> None:
        self.logs.extend(logs)


class StubNetworkAgent:
    name = "network-agent"

    def __init__(self, failed_operation_id: str | None = None) -> None:
        self.failed_operation_id = failed_operation_id
        self.calls: list[str] = []

    @property
    def tool_name(self) -> str:
        return "StubNetworkTool"

    @staticmethod
    def extract_commands(parameters) -> list[str]:
        return [parameters["command"]]

    async def execute(self, operation, mapping) -> NetworkExecutionResult:
        self.calls.append(operation.id)
        failed = operation.id == self.failed_operation_id
        return NetworkExecutionResult(
            operation_id=operation.id,
            operation_device_id=mapping.id,
            device_id=mapping.device_id,
            access_mode=mapping.access_mode,
            status=(
                NetworkExecutionStatus.FAILED
                if failed
                else NetworkExecutionStatus.SUCCESS
            ),
            error_message="failed" if failed else None,
        )


def build_task() -> TaskDetail:
    now = datetime.now(UTC)
    operations = [
        Operation(
            id=f"oper-{order}",
            task_id="task-1",
            operation_intent=f"STEP_{order}",
            display_order=order,
            operation_status=OperationStatus.PENDING,
            operation_parameters={"command": "show version"},
            created_at=now,
        )
        for order in (2, 1, 3)
    ]
    return TaskDetail(
        id="task-1",
        conversation_id="cons-1",
        source_message_id="mesg-1",
        user_id="user-1",
        input_message="Kiểm tra thiết bị",
        task_status=TaskStatus.PLANNING,
        task_type=TaskType.DIAGNOSIS,
        started_at=now,
        created_at=now,
        operations=operations,
    )


def test_execute_task_runs_operations_by_display_order() -> None:
    task = build_task()
    agent = StubNetworkAgent()
    service = StubExecutionService(task.operations)
    orchestrator = ExecutionOrchestrator(
        service,
        agent,
    )

    results = asyncio.run(orchestrator.execute_task(task))

    assert agent.calls == ["oper-1", "oper-2", "oper-3"]
    assert len(results) == 3
    assert service.tasks[-1].task_status == TaskStatus.SUCCESS
    assert all(
        operation.operation_status == OperationStatus.SUCCESS
        for operation in service.operations.values()
    )
    assert len(service.executions) == 6  # RUNNING và SUCCESS cho mỗi mapping.
    assert len(service.logs) == 3


def test_execute_task_stops_after_failed_operation() -> None:
    task = build_task()
    agent = StubNetworkAgent(failed_operation_id="oper-2")
    dependency = OperationDependency(
        id="opdp-1",
        operation_id="oper-3",
        depends_on_operation_id="oper-2",
        dependency_type=DependencyType.ON_SUCCESS,
        created_at=datetime.now(UTC),
    )
    service = StubExecutionService(task.operations, [dependency])
    orchestrator = ExecutionOrchestrator(
        service,
        agent,
    )

    asyncio.run(orchestrator.execute_task(task))

    assert agent.calls == ["oper-1", "oper-2"]
    assert service.operations["oper-3"].operation_status == OperationStatus.SKIPPED
    assert service.mappings["oper-3"].operation_device_status == (
        OperationDeviceStatus.SKIPPED
    )
    assert service.tasks[-1].task_status == TaskStatus.PARTIAL_SUCCESS
