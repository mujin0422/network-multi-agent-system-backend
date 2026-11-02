import re
from datetime import UTC, datetime

from app.domains.benchmark.schemas import (
    BenchmarkRunRecord,
    BenchmarkRunStatus,
    BenchmarkScenario,
    BenchmarkScenarioRecord,
)
from app.domains.benchmark.services import BenchmarkRunService, BenchmarkScenarioService
from app.domains.benchmark.schemas import BenchmarkAction
from app.domains.benchmark.utils import build_benchmark_action_commands
from app.domains.execution.schemas import AccessMode
from app.tools.network.schemas import CommandResult


class FakeEvaluationRepository:
    def save(self, _evaluation):
        return None


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
