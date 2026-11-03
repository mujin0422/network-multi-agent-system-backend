"""Static and schema checks for additional BGP scenarios on the GNS3 lab."""

import json
import re
from pathlib import Path

from app.domains.benchmark.schemas import BenchmarkScenario
from app.domains.benchmark.utils import build_benchmark_action_commands

BGP_SEED = Path("docker/postgres/seed/04_benchmark_bgp.sql")
EXPANSION_SEED = Path("docker/postgres/seed/03_benchmark_expansion.sql")
BASE_SEED = Path("docker/postgres/init/02_seed.sql.template")
COMPOSE = Path("docker-compose.yml")
LAB_CONFIG = Path("docs/device-configure.txt")

KEYS_PATTERN = re.compile(
    r"\(\s*'(benc-\d{6}-[0-9a-f]{8})'\s*,\s*'([a-z0-9][a-z0-9-]*)'"
)
JSON_PATTERN = re.compile(r"'(\{[^\n]+\})'::jsonb")

BGP_PEERS = {
    "pe1-ibgp-vpnv4-neighbor-shutdown": ("PE1", "10.2.2.2", 2204, 2204),
    "pe2-ibgp-vpnv4-neighbor-shutdown": ("PE2", "10.1.1.1", 2204, 2204),
    "ce-1a-ebgp-neighbor-shutdown": ("CE-1A", "192.168.1.1", 22041, 2204),
    "ce-1b-ebgp-neighbor-shutdown": ("CE-1B", "192.168.2.1", 22042, 2204),
    "ce-2a-ebgp-neighbor-shutdown": ("CE-2A", "192.168.3.1", 22043, 2204),
    "ce-2b-ebgp-neighbor-shutdown": ("CE-2B", "192.168.4.1", 22044, 2204),
}


def load_bgp_scenarios() -> dict[str, BenchmarkScenario]:
    text = BGP_SEED.read_text(encoding="utf-8")
    keys = KEYS_PATTERN.findall(text)
    definitions = [json.loads(match) for match in JSON_PATTERN.findall(text)]
    assert len(keys) == len(definitions) == len(BGP_PEERS)
    assert len({id_ for id_, _ in keys}) == len(keys)
    assert len({key for _, key in keys}) == len(keys)
    return {
        key: BenchmarkScenario.model_validate({
            "scenario_key": key,
            "version": "1.0",
            "name": key,
            "description": key,
            "topology": "mpls-core",
            "initial_message": key,
            **definition,
        })
        for (_, key), definition in zip(keys, definitions, strict=True)
    }


def test_bgp_seed_idempotent_and_does_not_override_existing_cases() -> None:
    text = BGP_SEED.read_text(encoding="utf-8")
    assert "ON CONFLICT (scenario_key) DO NOTHING" in text
    assert "BEGIN;" in text and "COMMIT;" in text
    assert "04_benchmark_bgp.sql:/docker-entrypoint-initdb.d/04_benchmark_bgp.sql" in COMPOSE.read_text(encoding="utf-8")

    existing = KEYS_PATTERN.findall(BASE_SEED.read_text(encoding="utf-8"))
    existing += KEYS_PATTERN.findall(EXPANSION_SEED.read_text(encoding="utf-8"))
    assert len(existing) == 27
    assert not (set(BGP_PEERS) & {key for _, key in existing})


def test_all_bgp_peers_match_reference_configuration() -> None:
    lab = LAB_CONFIG.read_text(encoding="utf-8")
    cases = load_bgp_scenarios()
    assert set(cases) == set(BGP_PEERS)

    for key, (device, ip, local_as, remote_as) in BGP_PEERS.items():
        case = cases[key]
        assert f"hostname {device}" in lab
        assert f"router bgp {local_as}" in lab
        assert f"neighbor {ip} remote-as {remote_as}" in lab

        assert len(case.preconditions) == 3
        assert len(case.injection) == len(case.cleanup) == 1
        assert case.fault_verification
        assert case.ground_truth[0].fault_type == "bgp_neighbor_admin_down"

        check = case.preconditions
        assert check[0].assertion.contains == f"neighbor {ip} remote-as {remote_as}"
        assert check[1].assertion.not_contains == f"neighbor {ip} shutdown"
        assert check[2].command == f"show ip bgp neighbors {ip} | include BGP state"
        assert check[2].assertion.contains == "Established"

        injected = case.injection[0]
        restored = case.cleanup[0]
        assert injected.device == restored.device == device
        assert injected.local_as == restored.local_as == local_as
        assert injected.neighbor_ip == restored.neighbor_ip == ip
        assert injected.action == "bgp_neighbor_shutdown"
        assert restored.action == "bgp_neighbor_no_shutdown"
        assert case.fault_verification[0].assertion.contains == f"neighbor {ip} shutdown"
        assert build_benchmark_action_commands(injected) == [
            f"router bgp {local_as}", f"neighbor {ip} shutdown"
        ]
        assert build_benchmark_action_commands(restored) == [
            f"router bgp {local_as}", f"no neighbor {ip} shutdown"
        ]
