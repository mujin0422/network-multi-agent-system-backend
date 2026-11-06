"""Kiểm tra Causal Evidence Gate không chấp nhận root cause thiếu dữ kiện."""

from app.diagnostics import (
    CausalClaimStatus,
    EvidenceSource,
    build_causal_scope,
    evaluate_causal_claims,
    parse_command_output,
)
from app.domains.evaluation.schemas import PredictedRootCause


def _evidence(device: str, command: str, output: str):
    return parse_command_output(
        command,
        output,
        EvidenceSource(
            execution_id=f"opdv-{device.lower()}",
            device_id=f"devc-{device.lower()}",
            device_name=device,
            command=command,
        ),
    )


def test_link_down_requires_matching_interface_evidence() -> None:
    evidence = _evidence(
        "P3",
        "show interfaces FastEthernet1/0",
        "FastEthernet1/0 is administratively down, line protocol is down",
    )
    causes = [
        PredictedRootCause(
            device="P3",
            interface="FastEthernet1/0",
            fault_type="link_down",
        ),
        PredictedRootCause(
            device="P3",
            interface="FastEthernet2/0",
            fault_type="link_down",
        ),
    ]

    result = evaluate_causal_claims(causes, evidence)

    assert result.confirmed == [causes[0]]
    assert result.suspected == [causes[1]]
    assert result.decisions[0].status == CausalClaimStatus.CONFIRMED
    assert result.decisions[0].evidence[0].execution_id == "opdv-p3"


def test_gate_rejects_real_but_out_of_scope_shutdown() -> None:
    evidence = [
        *_evidence(
            "P3",
            "show interfaces FastEthernet0/0",
            "FastEthernet0/0 is administratively down, line protocol is down",
        ),
        *_evidence(
            "P1",
            "show interfaces FastEthernet3/0",
            "FastEthernet3/0 is administratively down, line protocol is down",
        ),
    ]
    causes = [
        PredictedRootCause(
            device="P3", interface="FastEthernet0/0", fault_type="link_down"
        ),
        PredictedRootCause(
            device="P1", interface="FastEthernet3/0", fault_type="link_down"
        ),
    ]
    scope = build_causal_scope(
        "Chẩn đoán P3 FastEthernet0/0 bị mất kết nối",
        ["P1", "P3"],
    )

    result = evaluate_causal_claims(causes, evidence, scope)

    assert result.confirmed == [causes[0]]
    assert result.suspected == [causes[1]]
    assert "không nằm trong phạm vi" in result.decisions[1].reason


def test_default_route_missing_requires_negative_route_observation() -> None:
    evidence = _evidence(
        "P1",
        "show ip route 0.0.0.0",
        "Gateway of last resort is not set",
    )
    cause = PredictedRootCause(
        device="P1",
        interface=None,
        fault_type="default_route_missing",
    )

    result = evaluate_causal_claims([cause], evidence)

    assert result.confirmed == [cause]
    assert result.decisions[0].evidence[0].supporting_lines == [
        "Gateway of last resort is not set"
    ]


def test_mpls_disabled_requires_up_interface_config_and_mpls_table() -> None:
    evidence = [
        *_evidence(
            "P1",
            "show interfaces FastEthernet1/0",
            "FastEthernet1/0 is up, line protocol is up",
        ),
        *_evidence(
            "P1",
            "show running-config interface FastEthernet1/0",
            "interface FastEthernet1/0\n no shutdown",
        ),
        *_evidence(
            "P1",
            "show mpls interfaces",
            (
                "Interface IP Tunnel BGP Static Operational\n"
                "FastEthernet0/0 Yes (ldp) No No No Yes"
            ),
        ),
    ]
    cause = PredictedRootCause(
        device="P1",
        interface="FastEthernet1/0",
        fault_type="mpls_disabled",
    )

    result = evaluate_causal_claims([cause], evidence)

    assert result.confirmed == [cause]
    assert {item.evidence_type for item in result.decisions[0].evidence} == {
        "INTERFACE_STATUS",
        "INTERFACE_CONFIG",
        "MPLS_INTERFACE",
    }


def test_mpls_enabled_and_operational_is_not_confirmed_as_disabled() -> None:
    evidence = [
        *_evidence(
            "P1",
            "show interfaces FastEthernet1/0",
            "FastEthernet1/0 is up, line protocol is up",
        ),
        *_evidence(
            "P1",
            "show running-config interface FastEthernet1/0",
            "interface FastEthernet1/0\n mpls ip\n no shutdown",
        ),
        *_evidence(
            "P1",
            "show mpls interfaces",
            (
                "Interface IP Tunnel BGP Static Operational\n"
                "FastEthernet1/0 Yes (ldp) No No No Yes"
            ),
        ),
    ]
    cause = PredictedRootCause(
        device="P1",
        interface="FastEthernet1/0",
        fault_type="mpls_disabled",
    )

    result = evaluate_causal_claims([cause], evidence)

    assert result.suspected == [cause]
    assert result.decisions[0].missing_evidence == []


def test_mpls_disabled_reports_target_specific_missing_evidence() -> None:
    evidence = [
        *_evidence(
            "P1",
            "show interfaces FastEthernet1/0",
            "FastEthernet1/0 is up, line protocol is up",
        ),
        *_evidence(
            "P1",
            "show mpls interfaces",
            "Interface IP Tunnel BGP Static Operational",
        ),
    ]
    cause = PredictedRootCause(
        device="P1",
        interface="FastEthernet1/0",
        fault_type="mpls_disabled",
    )

    result = evaluate_causal_claims([cause], evidence)

    assert result.suspected == [cause]
    assert result.decisions[0].missing_evidence == ["INTERFACE_CONFIG"]


def test_mpls_evidence_from_another_interface_does_not_confirm_cause() -> None:
    evidence = [
        *_evidence(
            "P1",
            "show interfaces FastEthernet0/0",
            "FastEthernet0/0 is up, line protocol is up",
        ),
        *_evidence(
            "P1",
            "show running-config interface FastEthernet0/0",
            "interface FastEthernet0/0\n no shutdown",
        ),
        *_evidence(
            "P1",
            "show mpls interfaces",
            "Interface IP Tunnel BGP Static Operational",
        ),
    ]
    cause = PredictedRootCause(
        device="P1",
        interface="FastEthernet1/0",
        fault_type="mpls_disabled",
    )

    result = evaluate_causal_claims([cause], evidence)

    assert result.suspected == [cause]
    assert result.decisions[0].missing_evidence == [
        "INTERFACE_STATUS",
        "INTERFACE_CONFIG",
    ]


def test_ospf_area_mismatch_requires_topology_peer_interfaces() -> None:
    evidence = [
        *_evidence(
            "P3",
            "show ip ospf interface FastEthernet0/0",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.34.3/24, Area 1\n"
                " Process ID 1, Router ID 3.3.3.3, Network Type BROADCAST, Cost: 1"
            ),
        ),
        *_evidence(
            "P4",
            "show ip ospf interface FastEthernet0/0",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.34.4/24, Area 0\n"
                " Process ID 1, Router ID 4.4.4.4, Network Type BROADCAST, Cost: 1"
            ),
        ),
    ]
    cause = PredictedRootCause(
        device="P3",
        interface="FastEthernet0/0",
        fault_type="ospf_area_mismatch",
    )
    scope = build_causal_scope(
        "Chẩn đoán OSPF area trên P3 FastEthernet0/0",
        ["P3", "P4"],
        {
            "P3": [
                {
                    "device": "P4",
                    "local_interface": "FastEthernet0/0",
                    "peer_interface": "FastEthernet0/0",
                }
            ]
        },
    )

    result = evaluate_causal_claims([cause], evidence, scope)

    assert result.confirmed == [cause]
    assert {item.device_name for item in result.decisions[0].evidence} == {
        "P3",
        "P4",
    }


def test_link_down_does_not_confirm_unused_unassigned_interface() -> None:
    evidence = [
        *_evidence(
            "P2",
            "show ip interface brief",
            (
                "Interface IP-Address OK? Method Status Protocol\n"
                "FastEthernet3/0 unassigned YES NVRAM administratively down down"
            ),
        ),
        *_evidence(
            "P2",
            "show running-config interface FastEthernet3/0",
            "interface FastEthernet3/0\n no ip address\n shutdown",
        ),
    ]
    cause = PredictedRootCause(
        device="P2",
        interface="FastEthernet3/0",
        fault_type="link_down",
    )

    result = evaluate_causal_claims([cause], evidence)

    assert result.confirmed == []
    assert result.suspected == [cause]


def test_ospf_area_mismatch_can_confirm_from_device_wide_scope() -> None:
    evidence = [
        *_evidence(
            "P2",
            "show ip ospf interface",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.10.2/24, Area 1\n"
                " Process ID 1, Router ID 10.0.0.2, Network Type BROADCAST, Cost: 1"
            ),
        ),
        *_evidence(
            "P1",
            "show ip ospf interface FastEthernet0/0",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.10.1/24, Area 0\n"
                " Process ID 1, Router ID 10.0.0.1, Network Type BROADCAST, Cost: 1"
            ),
        ),
    ]
    cause = PredictedRootCause(
        device="P2",
        fault_type="ospf_area_mismatch",
    )
    scope = build_causal_scope(
        "Chẩn đoán neighbor OSPF trên P2",
        ["P1", "P2"],
        {
            "P2": [
                {
                    "device": "P1",
                    "local_interface": "FastEthernet0/0",
                    "peer_interface": "FastEthernet0/0",
                }
            ]
        },
    )

    result = evaluate_causal_claims([cause], evidence, scope)

    assert result.confirmed == [cause]


def test_ospf_area_result_is_node_scoped_when_request_names_no_interface() -> None:
    evidence = [
        *_evidence(
            "P2",
            "show ip ospf interface FastEthernet0/0",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.10.2/24, Area 1\n"
                " Process ID 1, Router ID 10.0.0.2, Network Type BROADCAST, Cost: 1"
            ),
        ),
        *_evidence(
            "P1",
            "show ip ospf interface FastEthernet0/0",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.10.1/24, Area 0\n"
                " Process ID 1, Router ID 10.0.0.1, Network Type BROADCAST, Cost: 1"
            ),
        ),
    ]
    interface_cause = PredictedRootCause(
        device="P2",
        interface="FastEthernet0/0",
        fault_type="ospf_area_mismatch",
    )
    scope = build_causal_scope(
        "Chẩn đoán neighbor OSPF trên P2",
        ["P1", "P2"],
        {
            "P2": [
                {
                    "device": "P1",
                    "local_interface": "FastEthernet0/0",
                    "peer_interface": "FastEthernet0/0",
                }
            ]
        },
    )

    result = evaluate_causal_claims([interface_cause], evidence, scope)

    assert len(result.confirmed) == 1
    assert result.confirmed[0].device == "P2"
    assert result.confirmed[0].interface is None


def test_ospf_node_scope_compares_network_statements_with_topology_peers() -> None:
    evidence = [
        *_evidence(
            "P2",
            "show running-config | section ospf",
            "router ospf 1\n network 10.0.0.0 0.255.255.255 area 1",
        ),
        *_evidence(
            "P1",
            "show running-config | section ospf",
            "router ospf 1\n network 10.0.0.0 0.255.255.255 area 0",
        ),
        *_evidence(
            "PE1",
            "show running-config | section ospf",
            "router ospf 1\n network 10.0.0.0 0.255.255.255 area 0",
        ),
    ]
    cause = PredictedRootCause(device="P2", fault_type="ospf_area_mismatch")
    scope = build_causal_scope(
        "Chẩn đoán neighbor OSPF trên P2",
        ["P1", "P2", "PE1"],
        {
            "P2": [
                {
                    "device": "P1",
                    "local_interface": "FastEthernet0/0",
                    "peer_interface": "FastEthernet0/0",
                },
                {
                    "device": "PE1",
                    "local_interface": "FastEthernet2/0",
                    "peer_interface": "FastEthernet2/0",
                },
            ]
        },
    )

    result = evaluate_causal_claims([cause], evidence, scope)

    assert result.confirmed == [cause]
    assert "network statement" in result.decisions[0].reason


def test_ospf_device_scope_requests_peer_area_before_confirming() -> None:
    evidence = [
        *_evidence(
            "P2",
            "show ip ospf interface",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.10.2/24, Area 1\n"
                " Process ID 1, Router ID 10.0.0.2, Network Type BROADCAST, Cost: 1"
            ),
        )
    ]
    cause = PredictedRootCause(device="P2", fault_type="ospf_area_mismatch")
    scope = build_causal_scope(
        "Chẩn đoán neighbor OSPF trên P2",
        ["P1", "P2"],
        {
            "P2": [
                {
                    "device": "P1",
                    "local_interface": "FastEthernet0/0",
                    "peer_interface": "FastEthernet0/0",
                }
            ]
        },
    )

    result = evaluate_causal_claims([cause], evidence, scope)

    assert result.suspected == [cause]
    assert result.decisions[0].recommended_checks[0].device == "P1"
    assert result.decisions[0].recommended_checks[0].commands == [
        "show ip ospf interface FastEthernet0/0"
    ]


def test_ospf_different_area_on_non_peer_does_not_confirm_mismatch() -> None:
    evidence = [
        *_evidence(
            "P3",
            "show ip ospf interface FastEthernet0/0",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.34.3/24, Area 1\n"
                " Process ID 1, Router ID 3.3.3.3, Network Type BROADCAST, Cost: 1"
            ),
        ),
        *_evidence(
            "P9",
            "show ip ospf interface FastEthernet9/0",
            (
                "FastEthernet9/0 is up, line protocol is up\n"
                " Internet Address 192.0.2.9/24, Area 0\n"
                " Process ID 1, Router ID 9.9.9.9, Network Type BROADCAST, Cost: 1"
            ),
        ),
    ]
    cause = PredictedRootCause(
        device="P3",
        interface="FastEthernet0/0",
        fault_type="ospf_area_mismatch",
    )
    scope = build_causal_scope(
        "Chẩn đoán OSPF area trên P3 FastEthernet0/0",
        ["P3", "P4", "P9"],
        {
            "P3": [
                {
                    "device": "P4",
                    "local_interface": "FastEthernet0/0",
                    "peer_interface": "FastEthernet0/0",
                }
            ]
        },
    )

    result = evaluate_causal_claims([cause], evidence, scope)

    assert result.suspected == [cause]
    assert result.decisions[0].recommended_checks[0].device == "P4"
    assert result.decisions[0].recommended_checks[0].commands == [
        "show ip ospf interface FastEthernet0/0"
    ]


def test_ospf_target_area_outlier_confirms_when_topology_peer_is_unavailable() -> None:
    evidence = [
        *_evidence(
            "P3",
            "show ip ospf interface",
            (
                "FastEthernet1/0 is up, line protocol is up\n"
                " Internet Address 10.0.35.3/24, Area 0\n"
                " Process ID 1, Router ID 3.3.3.3, Network Type BROADCAST, Cost: 1\n"
                " Neighbor Count is 1, Adjacent neighbor count is 1\n"
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.34.3/24, Area 1\n"
                " Process ID 1, Router ID 3.3.3.3, Network Type BROADCAST, Cost: 1\n"
                " Neighbor Count is 0, Adjacent neighbor count is 0"
            ),
        )
    ]
    cause = PredictedRootCause(
        device="P3",
        interface="FastEthernet0/0",
        fault_type="ospf_area_mismatch",
    )
    scope = build_causal_scope(
        "Chẩn đoán P3 FastEthernet0/0 mất OSPF adjacency",
        ["P3"],
    )

    result = evaluate_causal_claims([cause], evidence, scope)

    assert result.confirmed == [cause]


def test_ospf_same_area_on_peer_is_not_mismatch() -> None:
    evidence = [
        *_evidence(
            "P3",
            "show ip ospf interface FastEthernet0/0",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.34.3/24, Area 0\n"
                " Process ID 1, Router ID 3.3.3.3, Network Type BROADCAST, Cost: 1"
            ),
        ),
        *_evidence(
            "P4",
            "show ip ospf interface FastEthernet0/0",
            (
                "FastEthernet0/0 is up, line protocol is up\n"
                " Internet Address 10.0.34.4/24, Area 0\n"
                " Process ID 1, Router ID 4.4.4.4, Network Type BROADCAST, Cost: 1"
            ),
        ),
    ]
    cause = PredictedRootCause(
        device="P3",
        interface="FastEthernet0/0",
        fault_type="ospf_area_mismatch",
    )
    scope = build_causal_scope(
        "Chẩn đoán OSPF area trên P3 FastEthernet0/0",
        ["P3", "P4"],
        {
            "P3": [
                {
                    "device": "P4",
                    "local_interface": "FastEthernet0/0",
                    "peer_interface": "FastEthernet0/0",
                }
            ]
        },
    )

    result = evaluate_causal_claims([cause], evidence, scope)

    assert result.suspected == [cause]
    assert result.decisions[0].missing_evidence == []
    assert result.decisions[0].recommended_checks == []


def test_wrong_subnet_mask_requires_two_incompatible_link_networks() -> None:
    evidence = [
        *_evidence(
            "P1",
            "show running-config interface FastEthernet0/0",
            "interface FastEthernet0/0\n ip address 10.0.12.1 255.255.255.128",
        ),
        *_evidence(
            "P2",
            "show running-config interface FastEthernet0/0",
            "interface FastEthernet0/0\n ip address 10.0.13.2 255.255.255.0",
        ),
    ]
    cause = PredictedRootCause(
        device="P1",
        interface="FastEthernet0/0",
        fault_type="wrong_subnet_mask",
    )

    result = evaluate_causal_claims([cause], evidence)

    assert result.confirmed == [cause]
    assert len(result.decisions[0].evidence) == 2


def test_wrong_ip_requires_equal_masks_but_different_networks() -> None:
    evidence = [
        *_evidence(
            "P1",
            "show running-config interface FastEthernet0/0",
            "interface FastEthernet0/0\n ip address 10.0.99.1 255.255.255.0",
        ),
        *_evidence(
            "P2",
            "show running-config interface FastEthernet0/0",
            "interface FastEthernet0/0\n ip address 10.0.12.2 255.255.255.0",
        ),
    ]
    cause = PredictedRootCause(
        device="P1",
        interface="FastEthernet0/0",
        fault_type="wrong_ip_address",
    )

    result = evaluate_causal_claims([cause], evidence)

    assert result.confirmed == [cause]


def test_wrong_ip_uses_only_topology_peer_interface() -> None:
    evidence = [
        *_evidence(
            "CE-1B",
            "show running-config interface FastEthernet0/0",
            "interface FastEthernet0/0\n ip address 10.0.99.2 255.255.255.0",
        ),
        *_evidence(
            "PE1",
            "show running-config interface FastEthernet1/0",
            "interface FastEthernet1/0\n ip address 10.0.12.1 255.255.255.0",
        ),
        *_evidence(
            "P9",
            "show running-config interface FastEthernet9/0",
            "interface FastEthernet9/0\n ip address 192.0.2.1 255.255.255.0",
        ),
    ]
    cause = PredictedRootCause(
        device="CE-1B",
        interface="FastEthernet0/0",
        fault_type="wrong_ip_address",
    )
    scope = build_causal_scope(
        "Chẩn đoán CE-1B FastEthernet0/0 sai địa chỉ IP",
        ["CE-1B", "PE1", "P9"],
        {
            "CE-1B": [
                {
                    "device": "PE1",
                    "local_interface": "FastEthernet0/0",
                    "peer_interface": "FastEthernet1/0",
                }
            ]
        },
    )

    result = evaluate_causal_claims([cause], evidence, scope)

    assert result.confirmed == [cause]
    assert {item.device_name for item in result.decisions[0].evidence} == {
        "CE-1B",
        "PE1",
    }


def test_acl_claim_requires_both_attachment_and_deny_rule() -> None:
    cause = PredictedRootCause(
        device="P1",
        interface="FastEthernet0/0",
        fault_type="acl_traffic_block",
    )
    only_acl = _evidence(
        "P1",
        "show access-lists",
        "Extended IP access list 101\n deny ip any any",
    )

    incomplete = evaluate_causal_claims([cause], only_acl)
    complete = evaluate_causal_claims(
        [cause],
        [
            *only_acl,
            *_evidence(
                "P1",
                "show running-config interface FastEthernet0/0",
                "interface FastEthernet0/0\n ip access-group 101 in",
            ),
        ],
    )

    assert incomplete.suspected == [cause]
    assert complete.confirmed == [cause]
