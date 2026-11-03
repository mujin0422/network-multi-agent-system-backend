import re

import pytest
from pydantic import ValidationError
from datetime import UTC, datetime

from app.domains.benchmark.schemas import (
    BenchmarkRunRecord,
    BenchmarkRunStatus,
    BenchmarkScenario,
    BenchmarkScenarioRecord,
    BenchmarkScenarioUpdate,
)
from app.domains.benchmark.services import BenchmarkRunService, BenchmarkScenarioService
from app.domains.benchmark.schemas import BenchmarkAction
from app.domains.benchmark.utils import build_benchmark_action_commands
from app.domains.conversation.schemas import Message, MessageSender, MessageType
from app.domains.evaluation.schemas import EvaluationMetricType, EvaluationResult
from app.domains.execution.schemas import AccessMode, TaskDetail, TaskStatus, TaskType
from app.tools.network.schemas import CommandResult


class FakeEvaluationRepository:
    def __init__(self) -> None:
        self.saved = []

    def save(self, evaluation):
        self.saved.append(evaluation)


class FakeNetworkTool:
    def __init__(self) -> None:
        self.calls: list[tuple[str, AccessMode, list[str]]] = []

    def execute(self, device_id, access_mode, commands):
        self.calls.append((device_id, access_mode, commands))
        if access_mode == AccessMode.READ:
            state = "administratively down" if len(self.calls) > 1 else "is up"
            return [CommandResult(command=commands[0], output=state)]
        return [CommandResult(command="\n".join(commands), output="ok")]


class FakeScenarioRepository:
    def __init__(self) -> None:
        now = datetime.now(UTC)
        self.scenario = BenchmarkScenarioRecord.model_validate({
            "id": "benc-021126-a8f3612c", "scenario_key": "link-down",
            "version": "1.0", "name": "Link down",
            "description": "Scenario test", "topology": "lab",
            "initial_message": "Diagnose link down",
            "preconditions": [{"device": "P3", "command": "show interface", "assertion": {"contains": "is up"}}],
            "injection": [{"device": "P3", "action": "interface_shutdown", "interface": "FastEthernet2/0"}],
            "fault_verification": [{"device": "P3", "command": "show interface", "assertion": {"contains": "administratively down"}}],
            "ground_truth": [{"fault_type": "link_down", "device": "P3", "interface": "FastEthernet2/0"}],
            "evaluation_required_terms": ["P3", "FastEthernet2/0", "down"],
            "cleanup": [{"device": "P3", "action": "interface_no_shutdown", "interface": "FastEthernet2/0"}],
            "created_at": now, "last_updated_at": now,
        })
    def get_all(self):
        return [self.scenario]

    def get_by_id(self, _scenario_id):
        return self.scenario

    def get_by_key(self, scenario_key):
        return self.scenario if scenario_key == self.scenario.scenario_key else None

    def save(self, scenario):
        self.scenario = scenario


class FakeRunRepository:
    def __init__(self) -> None:
        self.runs: dict[str, BenchmarkRunRecord] = {}

    def get_all(self, limit=50):
        return list(self.runs.values())[:limit]

    def get_by_id(self, run_id):
        return self.runs[run_id]

    def save(self, run):
        self.runs[run.id] = run

    def get_by_source_message_id(self, source_message_id):
        return next(
            (run for run in self.runs.values()
             if run.source_message_id == source_message_id),
            None,
        )


def test_start_run_injects_fault_without_exposing_ground_truth() -> None:
    tool = FakeNetworkTool()
    service = BenchmarkRunService(
        FakeRunRepository(),
        FakeScenarioRepository(),
        FakeEvaluationRepository(),
        tool,
    )

    run = service.start("benc-021126-a8f3612c", "user-1")

    assert run.status == BenchmarkRunStatus.READY
    assert re.fullmatch(r"benr-\d{6}-[0-9a-f]{8}", run.id)
    assert not hasattr(run, "ground_truth")
    assert tool.calls[1] == (
        "P3",
        AccessMode.WRITE,
        ["interface FastEthernet2/0", "shutdown"],
    )


def test_scenario_detail_includes_complete_definition_for_editing() -> None:
    repository = FakeScenarioRepository()
    scenario = BenchmarkScenarioService(repository).get(repository.scenario.id)

    assert scenario.id == repository.scenario.id
    assert scenario.scenario_key == repository.scenario.scenario_key
    assert scenario.injection[0].action == "interface_shutdown"
    assert scenario.fault_verification[0].command == "show interface"
    assert scenario.ground_truth[0].fault_type == "link_down"
    assert scenario.cleanup[0].action == "interface_no_shutdown"
    assert scenario.evaluation_required_terms == ["P3", "FastEthernet2/0", "down"]


def test_create_scenario_generates_id_and_preserves_business_key() -> None:
    repository = FakeScenarioRepository()
    payload = BenchmarkScenario.model_validate(
        repository.scenario.model_copy(
            update={"scenario_key": "new-link-down"}
        ).model_dump()
    )

    created = BenchmarkScenarioService(repository).create(payload, "user-1")

    assert re.fullmatch(r"benc-\d{6}-[0-9a-f]{8}", created.id)
    assert created.scenario_key == "new-link-down"


def test_update_scenario_edits_typed_default_route_fault_without_changing_key() -> None:
    repository = FakeScenarioRepository()
    scenario_id = repository.scenario.id
    payload = BenchmarkScenarioUpdate.model_validate({
        "name": "CE-1A missing default route diagnosis",
        "injection": [
            {"device": "PE1", "action": "default_route_remove", "next_hop": "10.0.0.1"}
        ],
        "cleanup": [
            {"device": "PE1", "action": "default_route_add", "next_hop": "10.0.0.1"}
        ],
    })

    updated = BenchmarkScenarioService(repository).update(
        scenario_id, payload, "user-editor"
    )

    assert updated.scenario_key == "link-down"
    assert updated.name == "CE-1A missing default route diagnosis"
    assert updated.injection[0].action == "default_route_remove"
    assert updated.injection[0].next_hop == "10.0.0.1"
    assert updated.cleanup[0].action == "default_route_add"
    assert updated.cleanup[0].next_hop == "10.0.0.1"
    assert updated.last_updated_by == "user-editor"
    assert updated.ground_truth == repository.scenario.ground_truth


def test_builds_typed_configuration_fault_commands() -> None:
    """Các fault không phải link-down phải sinh đúng lệnh và không nhận raw command."""

    ospf = BenchmarkAction(
        device="P1", action="ospf_network_remove", process_id=1,
        network="10.0.0.0", wildcard="0.255.255.255", area=0,
    )
    acl = BenchmarkAction(
        device="PE1", action="acl_block", interface="FastEthernet3/0",
        acl_number=101, direction="in", source_network="172.16.1.0",
        source_wildcard="0.0.0.255",
    )

    assert build_benchmark_action_commands(ospf) == [
        "router ospf 1",
        "no network 10.0.0.0 0.255.255.255 area 0",
    ]
    assert build_benchmark_action_commands(acl)[-1] == "ip access-group 101 in"

    cleanup_acl = BenchmarkAction(
        device="PE1", action="acl_remove", interface="FastEthernet3/0",
        acl_number=101, direction="in",
    )
    assert build_benchmark_action_commands(cleanup_acl) == [
        "interface FastEthernet3/0",
        "no ip access-group 101 in",
        "exit",
        "no access-list 101",
    ]


def test_benchmark_evaluation_waits_for_final_response_after_approval() -> None:
    """Pending approval must not become a false FAIL or a prematurely completed run."""

    now = datetime.now(UTC)
    scenario = FakeScenarioRepository().scenario
    runs = FakeRunRepository()
    evaluations = FakeEvaluationRepository()
    service = BenchmarkRunService(runs, FakeScenarioRepository(), evaluations, FakeNetworkTool())
    run = BenchmarkRunRecord.model_validate({
        "id": "benr-021126-1234abcd",
        "scenario_id": scenario.id,
        "scenario_version": scenario.version,
        "scenario_name": scenario.name,
        "scenario_snapshot": scenario.model_dump(),
        "status": BenchmarkRunStatus.RUNNING,
        "started_by": "user-1",
        "initial_message": scenario.initial_message,
        "conversation_id": "cons-1",
        "source_message_id": "mesg-1",
        "started_at": now,
    })
    runs.save(run)
    task = TaskDetail(
        id="task-1",
        conversation_id="cons-1",
        source_message_id="mesg-1",
        user_id="user-1",
        input_message=scenario.initial_message,
        task_status=TaskStatus.RUNNING,
        task_type=TaskType.DIAGNOSIS,
        created_at=now,
    )
    waiting_message = Message(
        id="mesg-wait",
        conversation_id="cons-1",
        reply_to_message_id="mesg-1",
        sender_by=MessageSender.AGENT,
        message_type=MessageType.APPROVAL_REQUEST,
        message="Waiting for configuration approval.",
        created_at=now,
    )
    final_message = waiting_message.model_copy(update={
        "id": "mesg-final",
        "message_type": MessageType.FINAL_RESPONSE,
        "message": "P3 FastEthernet2/0 interface is down",
    })

    service.complete_for_task(task, waiting_message)
    assert runs.get_by_id(run.id).status == BenchmarkRunStatus.RUNNING
    assert evaluations.saved == []

    service.complete_for_task(task, final_message)
    completed = runs.get_by_id(run.id)
    assert completed.status == BenchmarkRunStatus.COMPLETED
    assert completed.task_id == task.id
    assert completed.evaluation_id is not None
    assert completed.evaluation_result == EvaluationResult.PASS
    assert len(evaluations.saved) == 1
    results = {metric.metric_type: metric.result for metric in evaluations.saved[0].metrics}
    assert results[EvaluationMetricType.GOAL] == EvaluationResult.PASS
    assert results[EvaluationMetricType.RCA] == EvaluationResult.PASS
    assert results[EvaluationMetricType.REMEDIATION] == EvaluationResult.NOT_APPLICABLE
    assert results[EvaluationMetricType.SAFETY] == EvaluationResult.NOT_APPLICABLE

    # A repeated post-approval background callback must not write a duplicate
    # evaluation for the same Task.
    service.complete_for_task(task, final_message)
    assert len(evaluations.saved) == 1


def test_bgp_neighbor_shutdown_and_cleanup_commands() -> None:
    disable = BenchmarkAction.model_validate({
        "device": "PE1",
        "action": "bgp_neighbor_shutdown",
        "local_as": 2204,
        "neighbor_ip": "10.2.2.2",
    })
    restore = disable.model_copy(update={"action": "bgp_neighbor_no_shutdown"})

    assert build_benchmark_action_commands(disable) == [
        "router bgp 2204",
        "neighbor 10.2.2.2 shutdown",
    ]
    assert build_benchmark_action_commands(restore) == [
        "router bgp 2204",
        "no neighbor 10.2.2.2 shutdown",
    ]


@pytest.mark.parametrize("neighbor_ip", ["", "999.1.1.1", "example.org", "10.1.1.1\\nexit"])
def test_bgp_neighbor_actions_reject_invalid_ipv4(neighbor_ip: str) -> None:
    with pytest.raises(ValidationError):
        BenchmarkAction.model_validate({
            "device": "PE1",
            "action": "bgp_neighbor_shutdown",
            "local_as": 2204,
            "neighbor_ip": neighbor_ip,
        })


@pytest.mark.parametrize("local_as", [0, 4294967296, None])
def test_bgp_neighbor_actions_require_valid_autonomous_system(local_as: int | None) -> None:
    with pytest.raises(ValidationError):
        BenchmarkAction.model_validate({
            "device": "PE1",
            "action": "bgp_neighbor_no_shutdown",
            "local_as": local_as,
            "neighbor_ip": "10.2.2.2",
        })
