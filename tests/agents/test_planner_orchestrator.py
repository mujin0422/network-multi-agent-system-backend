"""Tests cho Planner Agent và orchestration tạo execution plan."""

import asyncio
import json
from datetime import UTC, datetime

import pytest

from app.agents.orchestrator import PlanningOrchestrator
from app.agents.planner import PlannerAgent
from app.domains.conversation.schemas import Conversation, Message, MessageSender
from app.domains.execution.schemas import (
    AccessMode,
    DependencyType,
    DeviceRole,
    ExecutionPlanCreate,
    TaskCreate,
    TaskStatus,
    TaskType,
)
from tests.execution_service_factory import build_execution_service_stub
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


class CapturingChatModel(FakeChatModel):
    def __init__(self):
        self.messages = []

    async def ainvoke(self, messages):
        self.messages = messages
        return await super().ainvoke(messages)


class StubExecutionStore:
    def __init__(self):
        self.tasks = {}
        self.operations = []
        self.dependencies = []
        self.operation_devices = []
        self.activities = []

    def get_task_by_source_message_id(self, message_id):
        return next(
            (
                task
                for task in self.tasks.values()
                if task.source_message_id == message_id
            ),
            None,
        )

    def save_task(self, task):
        self.tasks[task.id] = task

    def get_task_by_id(self, task_id):
        return self.tasks.get(task_id)

    def get_all_tasks(self):
        return list(self.tasks.values())

    def get_all_operations_by_task_id(self, task_id):
        return [item for item in self.operations if item.task_id == task_id]

    def get_operation_by_id(self, operation_id):
        return next((item for item in self.operations if item.id == operation_id), None)

    def save_operation(self, operation):
        self.operations.append(operation)

    def save_execution_plan(self, task, operations, dependencies, operation_devices):
        self.tasks[task.id] = task
        self.operations.extend(operations)
        self.dependencies.extend(dependencies)
        self.operation_devices.extend(operation_devices)

    def get_all_task_activity_events_by_task_id(self, task_id):
        return [item for item in self.activities if item.task_id == task_id]

    def save_task_activity_event(self, event):
        self.activities.append(event)


class StubDeviceRepository:
    def __init__(self, device):
        self.device = device

    def get_all(self):
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
    execution_repository = StubExecutionStore()
    orchestrator = PlanningOrchestrator(
        PlannerAgent(FakeChatModel()),
        build_execution_service_stub(execution_repository),
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


def test_execution_service_persists_plan_and_returns_task_detail() -> None:
    """Regression: use the generated plan records, not undefined local variables."""

    repository = StubExecutionStore()
    service = build_execution_service_stub(repository)
    task = service.create_task(
        TaskCreate(
            conversation_id="cons-1",
            source_message_id="mesg-1",
            user_id="user-1",
            input_message="Read P1 routing table, then analyze it",
        )
    )
    plan = ExecutionPlanCreate.model_validate(
        {
            "task_type": "COMPOSITE",
            "operations": [
                {
                    "operation_intent": "GET_ROUTING_TABLE",
                    "operation_parameters": {"command": "show ip route"},
                    "devices": [
                        {
                            "device_id": "devc-1",
                            "device_role": "SOURCE",
                            "access_mode": "READ",
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
                            "dependency_type": "ON_SUCCESS",
                        }
                    ],
                },
            ],
        }
    )

    result = service.create_execution_plan(task.id, plan)

    assert result.id == task.id
    assert result.task_status == TaskStatus.PLANNING
    assert result.task_type == TaskType.COMPOSITE
    assert [operation.display_order for operation in result.operations] == [1, 2]
    assert repository.tasks[task.id].task_status == TaskStatus.PLANNING
    assert len(repository.operations) == 2
    assert len(repository.dependencies) == 1
    assert repository.dependencies[0].operation_id == result.operations[1].id
    assert repository.dependencies[0].depends_on_operation_id == result.operations[0].id
    assert len(repository.operation_devices) == 1
    assert repository.operation_devices[0].operation_id == result.operations[0].id
    assert repository.operation_devices[0].device_id == "devc-1"


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


@pytest.mark.parametrize(
    "content",
    [
        (
            "Đây là kế hoạch:\n```json\n"
            '{"task_type":"DIAGNOSIS","operations":[{'
            '"operation_intent":"GET_OSPF_CONFIG",'
            '"operation_parameters":{"command":"show running-config | section router ospf"},'
            '"devices":[{"device_id":"devc-1","device_role":"SOURCE",'
            '"access_mode":"READ"}],"dependencies":[]}]}\n```'
        ),
        [
            {"type": "text", "text": "Kết quả Planner:\n"},
            {
                "type": "text",
                "text": (
                    '{"task_type":"DIAGNOSIS","operations":[{'
                    '"operation_intent":"GET_OSPF_CONFIG",'
                    '"operation_parameters":{"command":"show ip ospf neighbor"},'
                    '"devices":[{"device_id":"devc-1",'
                    '"device_role":"SOURCE","access_mode":"READ"}],'
                    '"dependencies":[]}]}'
                ),
            },
        ],
        (
            "{'task_type':'DIAGNOSIS','operations':[{'operation_intent':"
            "'GET_OSPF_CONFIG','operation_parameters':{'command':"
            "'show ip ospf neighbor'},'devices':[{'device_id':'devc-1',"
            "'device_role':'SOURCE','access_mode':'READ'}],'dependencies':[]}]}"
        ),
    ],
)
def test_planner_parses_common_nvidia_json_response_shapes(content) -> None:
    """Planner vẫn đọc được JSON khi NIM bọc bằng prose, block hoặc dict literal."""

    plan = PlannerAgent._parse_plan(content)

    assert plan.task_type == TaskType.DIAGNOSIS
    assert plan.operations[0].devices[0].device_id == "devc-1"


def test_planner_wraps_single_operation_for_matched_diagnostic_playbook() -> None:
    content = {
        "operation_intent": "GET_OSPF_EVIDENCE",
        "operation_parameters": {"command": "show ip ospf interface"},
        "devices": [
            {
                "device_id": "devc-1",
                "device_role": "SOURCE",
                "access_mode": "READ",
            }
        ],
        "dependencies": [],
    }

    plan = PlannerAgent._parse_plan(
        content,
        default_task_type=TaskType.DIAGNOSIS,
    )

    assert plan.task_type == TaskType.DIAGNOSIS
    assert len(plan.operations) == 1
    assert plan.operations[0].operation_intent == "GET_OSPF_EVIDENCE"


def test_planner_does_not_guess_task_type_for_unscoped_single_operation() -> None:
    content = {
        "operation_intent": "GET_ROUTE",
        "operation_parameters": {"command": "show ip route"},
        "devices": [
            {
                "device_id": "devc-1",
                "device_role": "SOURCE",
                "access_mode": "READ",
            }
        ],
        "dependencies": [],
    }

    with pytest.raises(ValueError, match="ExecutionPlanCreate"):
        PlannerAgent._parse_plan(content)


def test_planner_correction_prompt_repeats_required_json_shape() -> None:
    prompt = PlannerAgent._build_correction_prompt(
        "{invalid}",
        ValueError("operation_parameters.command is required"),
    )

    assert "CẤU TRÚC TỐI THIỂU BẮT BUỘC" in prompt
    assert '"operation_parameters":{"command":"show ..."}' in prompt
    assert "không dùng hostname thay cho device_id" in prompt


def test_planner_includes_matched_diagnostic_playbook() -> None:
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
    model = CapturingChatModel()

    asyncio.run(PlannerAgent(model).plan("Chẩn đoán OSPF area mismatch", [device]))

    prompt = str(model.messages[-1].content)
    assert "MATCHED DIAGNOSTIC PLAYBOOKS" in prompt
    assert '"key": "ospf_area_mismatch"' in prompt
    assert "show ip ospf neighbor" in prompt


def test_planner_normalizes_write_commands_before_approval() -> None:
    plan = ExecutionPlanCreate.model_validate(
        {
            "task_type": "CONFIGURATION",
            "operations": [
                {
                    "operation_intent": "CONFIGURE_MPLS",
                    "operation_parameters": {
                        "commands": [
                            "configure terminal",
                            "interface GigabitEthernet0/0",
                            "mpls ip",
                            "exit",
                            "end",
                            "write memory",
                        ]
                    },
                    "devices": [
                        {
                            "device_id": "devc-1",
                            "device_role": "TARGET",
                            "access_mode": "WRITE",
                        }
                    ],
                }
            ],
        }
    )

    normalized = PlannerAgent._normalize_write_commands(plan)

    assert normalized.operations[0].operation_parameters == {
        "commands": ["interface GigabitEthernet0/0", "mpls ip", "exit"]
    }


def test_planner_rejects_physical_interface_missing_from_gns3_node() -> None:
    plan = ExecutionPlanCreate.model_validate(
        {
            "task_type": "CONFIGURATION",
            "operations": [
                {
                    "operation_intent": "CONFIGURE_INTERFACE",
                    "operation_parameters": {
                        "commands": ["interface GigabitEthernet0/0", "no shutdown"]
                    },
                    "devices": [
                        {
                            "device_id": "devc-p3",
                            "device_role": "TARGET",
                            "access_mode": "WRITE",
                        }
                    ],
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="FastEthernet0/0"):
        PlannerAgent._validate_interface_commands(
            plan,
            {"devc-p3": ["FastEthernet0/0", "FastEthernet1/0"]},
        )
