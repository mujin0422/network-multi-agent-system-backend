"""Kiểm tra registry và selection của diagnostic playbook."""

from app.diagnostics import (
    DiagnosticEvidence,
    EvidenceSource,
    EvidenceType,
    evaluate_evidence_coverage,
    get_playbook,
    list_playbooks,
    select_playbooks,
)
from app.domains.evaluation.schemas import FaultType


def test_registry_covers_all_benchmark_fault_types() -> None:
    expected = {
        FaultType.LINK_DOWN,
        FaultType.LOOPBACK_ADMIN_DOWN,
        FaultType.OSPF_NETWORK_MISSING,
        FaultType.OSPF_AREA_MISMATCH,
        FaultType.MPLS_DISABLED,
        FaultType.DEFAULT_ROUTE_MISSING,
        FaultType.WRONG_SUBNET_MASK,
        FaultType.WRONG_IP_ADDRESS,
        FaultType.ACL_TRAFFIC_BLOCK,
        FaultType.BGP_NEIGHBOR_ADMIN_DOWN,
    }
    actual = {fault for playbook in list_playbooks() for fault in playbook.fault_types}
    assert actual == expected


def test_select_playbooks_matches_ospf_area_without_unrelated_playbook() -> None:
    selected = select_playbooks("Chẩn đoán OSPF area mismatch giữa P1 và P2")
    keys = {playbook.key for playbook in selected}
    assert "ospf_area_mismatch" in keys
    assert "mpls_disabled" not in keys


def test_get_playbook_accepts_key_and_fault_type() -> None:
    by_key = get_playbook("wrong_subnet_mask")
    by_fault = get_playbook(FaultType.WRONG_SUBNET_MASK)
    assert by_key is not None
    assert by_key is by_fault
    assert by_key.required_evidence


def test_evidence_coverage_reports_missing_required_types() -> None:
    evidence = DiagnosticEvidence(
        evidence_type=EvidenceType.MPLS_INTERFACE,
        resource_id="node/p1",
        source=EvidenceSource(
            execution_id="opdv-1",
            device_id="devc-1",
            device_name="P1",
            command="show mpls interfaces",
        ),
        raw_output="FastEthernet0/0 Yes",
    )

    coverage = evaluate_evidence_coverage(["mpls_disabled"], [evidence])

    assert coverage.coverage == 1 / 3
    assert coverage.missing == [
        EvidenceType.INTERFACE_CONFIG,
        EvidenceType.INTERFACE_STATUS,
    ]
    assert coverage.complete is False
