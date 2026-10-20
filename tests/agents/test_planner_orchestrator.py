"""Tests cho Planner Agent và orchestration tạo execution plan."""

import asyncio
import json
from datetime import UTC, datetime

from app.agents.orchestrator import PlanningOrchestrator
from app.agents.planner import PlannerAgent
from app.domains.conversation.schemas import Conversation, Message, MessageSender
from app.domains.execution.schemas import (
    AccessMode,
    DependencyType,
    DeviceRole,
    TaskType,
)
from app.domains.execution.services import ExecutionService
from app.domains.inventory.schemas import Device
from app.domains.inventory.services import DeviceService


class FakeChatModel:
    async def ainvoke(self, messages):
        return json.dumps(
            {
                "task_type": TaskType.COMPOSITE,
                "operations": [
                    {
                        "operation_intent": "GET_ROUTING_TABLE",
                        "operation_parameters": {"command": "show ip route"},
                        "devices": [
                            {
                                "device_id": "devc-1",
                                "device_role": DeviceRole.SOURCE,
                                "access_mode": AccessMode.READ,
                            }
                        ],
                        "dependencies": [],
                    },
                    {
                        "operation_intent": "ANALYZE_ROUTING_DATA",
                        "operation_parameters": {},
                        "devices": [],
                        "dependencies": [
                            {
                                "depends_on_order": 1,
                                "dependency_type": DependencyType.ON_SUCCESS,
                            }
                        ],
                    },
                ],
            }
        )


class FakeRetryChatModel(FakeChatModel):
    def __init__(self):
        self.call_count = 0

    async def ainvoke(self, messages):
        self.call_count += 1
        if self.call_count == 1:
            return json.dumps(
                {
                    "task_type": TaskType.INFORMATION_RETRIEVAL,
                    "operations": [
                        {
                            "operation_intent": "GET_ROUTING_TABLE",
                            "operation_parameters": {},
                            "devices": [
                                {
                                    "device_id": "devc-1",
                                    "device_role": DeviceRole.SOURCE,
                                    "access_mode": AccessMode.READ,
                                }
                            ],
                            "dependencies": [],
                        }
                    ],
                }
            )
        return await super().ainvoke(messages)


class StubExecutionRepository:
    def __init__(self):
        self.tasks = {}
        self.operations = []
        self.dependencies = []
        self.operation_devices = []

    def find_task_by_source_message(self, message_id):
        return next(
            (task for task in self.tasks.values() if task.source_message_id == message_id),
            None,
        )

    def save_task(self, task):
        self.tasks[task.id] = task

    def get_task(self, task_id):
        return self.tasks.get(task_id)

    def list_tasks(self):
        return list(self.tasks.values())

    def list_operations(self, task_id):
        return [item for item in self.operations if item.task_id == task_id]

    def get_operation(self, operation_id):
        return next((item for item in self.operations if item.id == operation_id), None)

    def save_operation(self, operation):
        self.operations.append(operation)

    def save_execution_plan(self, task, operations, dependencies, operation_devices):
        self.tasks[task.id] = task
        self.operations.extend(operations)
        self.dependencies.extend(dependencies)
        self.operation_devices.extend(operation_devices)


class StubDeviceRepository:
    def __init__(self, device):
        self.device = device

    def list(self):
        return [self.device]


def test_orchestrator_creates_task_operations_dependencies_and_devices() -> None:
    now = datetime.now(UTC)
    device = Device(
        id="devc-1",
        credential_id=None,
        brand_id="brnd-1",
        category_id="catg-1",
        hostname="P1",
        host="192.0.2.1",
        port=22,
        device_type="cisco_ios",
        location=None,
        created_by="user-1",
        last_updated_by="user-1",
        created_at=now,
        last_updated_at=now,
    )
    execution_repository = StubExecutionRepository()
    orchestrator = PlanningOrchestrator(
        PlannerAgent(FakeChatModel()),
        ExecutionService(execution_repository),
        DeviceService(StubDeviceRepository(device)),
    )
    conversation = Conversation(
        id="cons-1",
        user_id="user-1",
        title="Routing",
        created_at=now,
        last_updated_at=now,
    )
    message = Message(
        id="mesg-1",
        conversation_id=conversation.id,
        sender_by=MessageSender.USER,
        message="Lấy routing table P1 rồi phân tích",
        created_at=now,
    )

    task = asyncio.run(orchestrator.plan_user_message(conversation, message))

    assert task.task_type == TaskType.COMPOSITE
    assert [item.display_order for item in task.operations] == [1, 2]
    assert len(execution_repository.dependencies) == 1
    assert execution_repository.dependencies[0].operation_id == task.operations[1].id
    assert len(execution_repository.operation_devices) == 1
    assert execution_repository.operation_devices[0].device_id == device.id


def test_planner_retries_when_model_omits_device_command() -> None:
    now = datetime.now(UTC)
    device = Device(
        id="devc-1",
        credential_id=None,
        brand_id="brnd-1",
        category_id="catg-1",
        hostname="P1",
        host="192.0.2.1",
        port=22,
        device_type="cisco_ios",
        location=None,
        created_by="user-1",
        last_updated_by="user-1",
        created_at=now,
        last_updated_at=now,
    )
    model = FakeRetryChatModel()

    plan = asyncio.run(PlannerAgent(model).plan("Lấy routing table P1", [device]))

    assert model.call_count == 2
    assert plan.operations[0].operation_parameters == {"command": "show ip route"}
