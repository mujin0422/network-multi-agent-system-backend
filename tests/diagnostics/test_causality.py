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
