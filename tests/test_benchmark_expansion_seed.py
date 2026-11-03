"""Regression checks for the optional/idempotent GNS3 benchmark expansion seed."""

import json
import re
from pathlib import Path

from app.domains.benchmark.schemas import BenchmarkScenario

BASE_SEED = Path("docker/postgres/init/02_seed.sql.template")
EXPANSION_SEED = Path("docker/postgres/seed/03_benchmark_expansion.sql")
COMPOSE_FILE = Path("docker-compose.yml")

ID_KEY_PATTERN = re.compile(
    r"\(\s*'(benc-\d{6}-[0-9a-f]{8})'\s*,\s*'([a-z0-9][a-z0-9-]*)'"
)
JSON_PATTERN = re.compile(r"'(\{[^\n]+\})'::jsonb")


def load_expansion() -> list[BenchmarkScenario]:
    text = EXPANSION_SEED.read_text(encoding="utf-8")
    ids_and_keys = ID_KEY_PATTERN.findall(text)
    definitions = [json.loads(blob) for blob in JSON_PATTERN.findall(text)]

    assert len(ids_and_keys) == len(definitions) == 17
    assert len({item[0] for item in ids_and_keys}) == 17
    assert len({item[1] for item in ids_and_keys}) == 17

    return [
        BenchmarkScenario.model_validate({
            "scenario_key": key,
            "version": "1.0",
            "name": key,
            "description": key,
            "topology": "mpls-core",
            "initial_message": key,
            **definition,
        })
        for (_, key), definition in zip(ids_and_keys, definitions, strict=True)
    ]


def test_expansion_is_idempotent_and_bootstrapped_only_on_new_volumes() -> None:
    text = EXPANSION_SEED.read_text(encoding="utf-8")
    compose = COMPOSE_FILE.read_text(encoding="utf-8")
    assert "ON CONFLICT (scenario_key) DO NOTHING;" in text
    assert "BEGIN;" in text and "COMMIT;" in text
    assert "03_benchmark_expansion.sql:/docker-entrypoint-initdb.d/03_benchmark_expansion.sql" in compose


def test_expanded_cases_are_valid_and_do_not_duplicate_existing_scenarios() -> None:
    expansion = load_expansion()
    original = BASE_SEED.read_text(encoding="utf-8")
    original_keys = {key for _, key in ID_KEY_PATTERN.findall(original)}

    assert len(original_keys) == 10
    assert not original_keys.intersection(scenario.scenario_key for scenario in expansion)
    assert all(scenario.injection and scenario.cleanup for scenario in expansion)
    assert all(scenario.preconditions and scenario.fault_verification for scenario in expansion)
    assert all(scenario.ground_truth and scenario.evaluation_required_terms for scenario in expansion)


def test_expansion_uses_only_known_lab_devices_and_inverse_cleanup() -> None:
    cases = load_expansion()
    original = BASE_SEED.read_text(encoding="utf-8")

    # Seed inventory is the source of truth; do not invent router/switch hostnames.
    hostnames = set(re.findall(
        r"'(P1|P2|PE1|PE2|CE-1A|CE-1B|CE-2A|CE-2B|Switch1|Switch2|Switch3|Switch4|P3)'\s*,\s*'host\.docker\.internal'",
        original,
    ))
    assert hostnames

    inverse = {
        "interface_shutdown": "interface_no_shutdown",
        "interface_no_shutdown": "interface_shutdown",
        "mpls_disable": "mpls_enable",
        "mpls_enable": "mpls_disable",
        "ospf_network_remove": "ospf_network_add",
        "ospf_network_add": "ospf_network_remove",
        "default_route_add": "default_route_remove",
        "default_route_remove": "default_route_add",
        "acl_block": "acl_remove",
        "acl_remove": "acl_block",
        "interface_ip_set": "interface_ip_set",
    }

    for scenario in cases:
        assert scenario.topology == "mpls-core"
        assert len(scenario.cleanup) == len(scenario.injection)
        for step in [
            *scenario.preconditions,
            *scenario.injection,
            *scenario.fault_verification,
            *scenario.cleanup,
            *scenario.ground_truth,
        ]:
            assert step.device in hostnames

        for injected, cleanup in zip(
            reversed(scenario.injection), scenario.cleanup, strict=True
        ):
            assert cleanup.action == inverse[injected.action]
            assert cleanup.device == injected.device
            if injected.interface:
                assert cleanup.interface == injected.interface
            if injected.action.startswith("ospf_"):
                assert cleanup.process_id == injected.process_id
                assert cleanup.network == injected.network
                assert cleanup.wildcard == injected.wildcard
                assert cleanup.area == injected.area
            if injected.action == "acl_block":
                assert cleanup.acl_number == injected.acl_number
                assert cleanup.direction == injected.direction
            if injected.action == "interface_ip_set":
                assert (cleanup.ip_address, cleanup.subnet_mask) != (
                    injected.ip_address, injected.subnet_mask
                )


def test_expanded_scenarios_cover_several_fault_families() -> None:
    keys = {scenario.scenario_key for scenario in load_expansion()}
    for family in ("link-down", "trunk-down", "ospf", "mpls", "wrong-ip", "acl", "loopback"):
        assert any(family in key for key in keys), family
