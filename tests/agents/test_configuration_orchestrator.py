"""Kiểm tra orchestration riêng của Configuration Agent."""

import asyncio
from datetime import UTC, datetime

from app.agents.orchestrator import ConfigurationOrchestrator
from app.domains.execution.schemas import (
    ActivityActorType,
    ActivityEventType,
    ExecutionPlanCreate,
)
from app.domains.inventory.schemas import Device


class ConfigurationAgentStub:
    async def generate(self, plan, _devices, _interfaces):
        operation = plan.operations[0]
        configured = operation.model_copy(
            update={
                "operation_parameters": {
                    "commands": ["interface FastEthernet0/0", "mpls ip"]
                }
            }
        )
        return plan.model_copy(update={"operations": [configured]})


class ExecutionServiceStub:
    def __init__(self) -> None:
        self.activities: list[tuple] = []

    def record_activity(self, *args, **kwargs) -> None:
        self.activities.append((args, kwargs))


def test_configuration_orchestrator_generates_commands_and_records_activity() -> None:
    plan = ExecutionPlanCreate.model_validate(
        {
            "task_type": "CONFIGURATION",
            "operations": [
                {
                    "operation_intent": "ENABLE_MPLS",
                    "operation_parameters": {
                        "configuration_requirements": {
                            "interface": "FastEthernet0/0",
                            "mpls": True,
                        }
                    },
                    "devices": [
                        {
                            "device_id": "devc-1",
                            "device_role": "TARGET",
                            "access_mode": "WRITE",
                        }
                    ],
                    "dependencies": [],
                }
            ],
        }
    )
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
    execution_service = ExecutionServiceStub()
    orchestrator = ConfigurationOrchestrator(
        ConfigurationAgentStub(),
        execution_service,
    )

    configured = asyncio.run(
        orchestrator.configure_plan(
            "task-1",
            plan,
            [device],
            {"devc-1": ["FastEthernet0/0"]},
        )
    )

    assert configured.operations[0].operation_parameters["commands"] == [
        "interface FastEthernet0/0",
        "mpls ip",
    ]
    assert [activity[0][1] for activity in execution_service.activities] == [
        ActivityActorType.CONFIGURATION,
        ActivityActorType.CONFIGURATION,
    ]
    assert [activity[0][2] for activity in execution_service.activities] == [
        ActivityEventType.CONFIGURATION_STARTED,
        ActivityEventType.CONFIGURATION_COMPLETED,
    ]
