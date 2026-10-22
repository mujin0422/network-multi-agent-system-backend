"""Kiểm thử luồng Task -> Operation -> Network Agent."""

import asyncio
from datetime import UTC, datetime

from app.agents.network import NetworkExecutionResult, NetworkExecutionStatus
from app.agents.orchestrator import ExecutionOrchestrator
from app.domains.execution.schemas import (
    AccessMode,
    ApprovalStatus,
    DependencyType,
    DeviceRole,
    Operation,
    OperationDeviceApproval,
    OperationDependency,
    OperationDeviceStatus,
    OperationStatus,
    RiskLevel,
    TaskDetail,
    TaskStatus,
    TaskType,
    TaskOperationDevice,
)
from app.domains.execution.utils import build_approval_request_hash


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
        self.approvals: dict[str, OperationDeviceApproval] = {}
        self.activities = []
        self.task: TaskDetail | None = None

    def get_operation(self, operation_id: str) -> Operation:
        return self.operations[operation_id]

    def get_task(self, task_id: str) -> TaskDetail:
        assert self.task is not None and self.task.id == task_id
        return self.task.model_copy(
            update={"operations": list(self.operations.values())}
        )

    def list_operation_devices(self, operation_id: str) -> list:
        return [self.mappings[operation_id]]

    def get_operation_device(self, operation_device_id: str) -> TaskOperationDevice:
        return next(
            mapping
            for mapping in self.mappings.values()
            if mapping.id == operation_device_id
        )

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

    def record_activity(self, task_id, actor_type, event_type, event_status=None, **kwargs):
        self.activities.append(
            {
                "task_id": task_id,
                "actor_type": actor_type,
                "event_type": event_type,
                "event_status": event_status,
                **kwargs,
            }
        )

    def get_operation_device_approval(
        self,
        operation_device_id: str,
    ) -> OperationDeviceApproval | None:
        return self.approvals.get(operation_device_id)

    def create_operation_device_approval(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        commands: list[str],
        request_hash: str,
    ) -> OperationDeviceApproval:
        now = datetime.now(UTC)
        approval = OperationDeviceApproval(
            id=f"aprv-{mapping.id}",
            operation_device_id=mapping.id,
            approval_status=ApprovalStatus.PENDING,
            risk_level=RiskLevel.HIGH,
            requested_by="execution-orchestrator",
            reason=f"Phê duyệt {operation.operation_intent}",
            commands_snapshot=commands,
            request_hash=request_hash,
            requested_at=now,
            created_at=now,
        )
        self.approvals[mapping.id] = approval
        return approval

    def expire_operation_approval(self, approval_id: str) -> None:
        for mapping_id, approval in self.approvals.items():
            if approval.id == approval_id:
                self.approvals[mapping_id] = approval.model_copy(
                    update={"approval_status": ApprovalStatus.EXPIRED}
                )
                return


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


def test_write_mapping_waits_without_approved_request() -> None:
    task = build_task().model_copy(update={"operations": [build_task().operations[0]]})
    operation = task.operations[0]
    service = StubExecutionService(task.operations)
    service.mappings[operation.id] = service.mappings[operation.id].model_copy(
        update={"device_role": DeviceRole.TARGET, "access_mode": AccessMode.WRITE}
    )
    agent = StubNetworkAgent()

    results = asyncio.run(ExecutionOrchestrator(service, agent).execute_task(task))

    assert results == []
    assert agent.calls == []
    assert service.operations[operation.id].operation_status == (
        OperationStatus.WAITING_APPROVAL
    )
    assert service.mappings[operation.id].operation_device_status == (
        OperationDeviceStatus.WAITING_APPROVAL
    )
    assert service.approvals[service.mappings[operation.id].id].approval_status == (
        ApprovalStatus.PENDING
    )
    assert service.tasks[-1].task_status == TaskStatus.RUNNING
    assert service.tasks[-1].completed_at is None


def test_write_mapping_runs_only_when_snapshot_and_hash_match() -> None:
    task = build_task().model_copy(update={"operations": [build_task().operations[0]]})
    operation = task.operations[0]
    service = StubExecutionService(task.operations)
    mapping = service.mappings[operation.id].model_copy(
        update={"device_role": DeviceRole.TARGET, "access_mode": AccessMode.WRITE}
    )
    service.mappings[operation.id] = mapping
    commands = [operation.operation_parameters["command"]]
    now = datetime.now(UTC)
    service.approvals[mapping.id] = OperationDeviceApproval(
        id="aprv-1",
        operation_device_id=mapping.id,
        approval_status=ApprovalStatus.APPROVED,
        risk_level=RiskLevel.HIGH,
        requested_by="orchestrator",
        reason="Thực hiện cấu hình",
        commands_snapshot=commands,
        request_hash=build_approval_request_hash(mapping.id, commands),
        decided_by="user-approver",
        requested_at=now,
        decided_at=now,
        created_at=now,
    )
    agent = StubNetworkAgent()

    asyncio.run(ExecutionOrchestrator(service, agent).execute_task(task))

    assert agent.calls == [operation.id]
    assert service.mappings[operation.id].operation_device_status == (
        OperationDeviceStatus.SUCCESS
    )


def test_resume_after_approval_continues_the_parent_task() -> None:
    task = build_task().model_copy(update={"operations": [build_task().operations[0]]})
    operation = task.operations[0]
    service = StubExecutionService(task.operations)
    service.task = task
    mapping = service.mappings[operation.id].model_copy(
        update={
            "device_role": DeviceRole.TARGET,
            "access_mode": AccessMode.WRITE,
            "operation_device_status": OperationDeviceStatus.WAITING_APPROVAL,
        }
    )
    service.mappings[operation.id] = mapping
    commands = [operation.operation_parameters["command"]]
    now = datetime.now(UTC)
    service.approvals[mapping.id] = OperationDeviceApproval(
        id="aprv-resume",
        operation_device_id=mapping.id,
        approval_status=ApprovalStatus.APPROVED,
        risk_level=RiskLevel.HIGH,
        requested_by="orchestrator",
        reason="Thực hiện cấu hình",
        commands_snapshot=commands,
        request_hash=build_approval_request_hash(mapping.id, commands),
        decided_by="user-approver",
        requested_at=now,
        decided_at=now,
        created_at=now,
    )
    agent = StubNetworkAgent()

    results = asyncio.run(
        ExecutionOrchestrator(service, agent).resume_after_approval(mapping.id)
    )

    assert len(results) == 1
    assert agent.calls == [operation.id]
    assert service.tasks[-1].task_status == TaskStatus.SUCCESS


def test_write_mapping_rejects_changed_commands_after_approval() -> None:
    task = build_task().model_copy(update={"operations": [build_task().operations[0]]})
    operation = task.operations[0]
    service = StubExecutionService(task.operations)
    mapping = service.mappings[operation.id].model_copy(
        update={"device_role": DeviceRole.TARGET, "access_mode": AccessMode.WRITE}
    )
    service.mappings[operation.id] = mapping
    now = datetime.now(UTC)
    approved_commands = ["configure terminal"]
    service.approvals[mapping.id] = OperationDeviceApproval(
        id="aprv-1",
        operation_device_id=mapping.id,
        approval_status=ApprovalStatus.APPROVED,
        risk_level=RiskLevel.HIGH,
        requested_by="orchestrator",
        reason="Thực hiện cấu hình",
        commands_snapshot=approved_commands,
        request_hash=build_approval_request_hash(mapping.id, approved_commands),
        decided_by="user-approver",
        requested_at=now,
        decided_at=now,
        created_at=now,
    )
    agent = StubNetworkAgent()

    asyncio.run(ExecutionOrchestrator(service, agent).execute_task(task))

    assert agent.calls == []
    assert service.mappings[operation.id].operation_device_status == (
        OperationDeviceStatus.FAILED
    )
    assert "không khớp snapshot" in service.mappings[operation.id].error_message
