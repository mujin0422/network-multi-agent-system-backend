"""Kiểm tra Configuration Agent tách sinh command khỏi Planner."""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from app.agents.configuration import ConfigurationAgent
from app.domains.execution.schemas import ExecutionPlanCreate
from app.domains.inventory.schemas import Device


class FakeConfigurationModel:
    async def ainvoke(self, _messages):
        return SimpleNamespace(
            content=(
                '{"configurations":[{"operation_order":1,"commands":'
                '["configure terminal","interface FastEthernet0/0",'
                '"no shutdown","end","write memory"]}]}'
            )
        )


class FailingConfigurationModel:
    async def ainvoke(self, _messages):
        raise AssertionError("Không được gọi LLM khi proposal đã có command")


def test_configuration_agent_generates_and_normalizes_write_commands() -> None:
    plan = ExecutionPlanCreate.model_validate(
        {
            "task_type": "CONFIGURATION",
            "operations": [
                {
                    "operation_intent": "ENABLE_INTERFACE",
                    "operation_parameters": {
                        "configuration_requirements": {
                            "interface": "FastEthernet0/0",
                            "enabled": True,
                        }
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

    result = asyncio.run(
        ConfigurationAgent(FakeConfigurationModel()).generate(
            plan,
            [device],
            {"devc-1": ["FastEthernet0/0"]},
        )
    )

    assert result.operations[0].operation_parameters == {
        "commands": ["interface FastEthernet0/0", "no shutdown"]
    }


def test_configuration_agent_preserves_commands_loaded_from_saved_proposal() -> None:
    plan = ExecutionPlanCreate.model_validate(
        {
            "task_type": "CONFIGURATION",
            "operations": [
                {
                    "operation_intent": "APPLY_PROPOSED_CONFIGURATION_P1",
                    "operation_parameters": {
                        "commands": ["interface FastEthernet4/0", "mpls ip"],
                        "proposal_source_message_id": "mesg-1",
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

    result = asyncio.run(
        ConfigurationAgent(FailingConfigurationModel()).generate(plan, [], {})
    )

    assert result == plan
