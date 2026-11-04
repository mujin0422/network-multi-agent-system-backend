"""Structured NIKA 0.2-style scoring: pair sets, localization, fault typing."""

import pytest

from app.domains.benchmark.schemas.common import BenchmarkRootCause
from app.domains.benchmark.utils.structured_rca import score_structured_rca


def _truth(*items: tuple[str, str | None, str]):
    return [
        BenchmarkRootCause(device=device, interface=interface, fault_type=fault)
        for device, interface, fault in items
    ]


def _submission(*items: tuple[str, str | None, str], anomaly=True):
    return {
        "is_anomaly": anomaly,
        "root_causes": [
            {"device": device, "interface": interface, "fault_type": fault}
            for device, interface, fault in items
        ],
    }


def test_exact_pair_set_matches_nika_joint_rca_and_goal() -> None:
    result = score_structured_rca(
        _truth(("P1", "FastEthernet0/0", "link_down")),
        _submission(("p1", "fastethernet0/0", "LINK_DOWN")),
    )
    assert result["detection_score"] == 1
    assert result["rca_precision"] == 1
    assert result["rca_recall"] == 1
    assert result["rca_f1"] == 1
    assert result["localization_f1"] == 1
    assert result["fault_type_f1"] == 1
    assert result["task_goal_met"] is True
    assert result["predicted_root_causes"] == [
        {"resource_id": "interface/p1/fastethernet0/0", "fault_type": "link_down"}
    ]


@pytest.mark.parametrize(
    "pred,localization,typing",
    [
        (("P2", "FastEthernet0/0", "link_down"), 0.0, 1.0),
        (("P1", "FastEthernet0/1", "link_down"), 0.0, 1.0),
        (("P1", "FastEthernet0/0", "mpls_disabled"), 1.0, 0.0),
        (("P1", None, "link_down"), 0.0, 1.0),
    ],
)
def test_wrong_device_interface_or_cause_cannot_score_pass(
    pred, localization, typing,
) -> None:
    result = score_structured_rca(
        _truth(("P1", "FastEthernet0/0", "link_down")), _submission(pred)
    )
    assert result["rca_f1"] == 0.0
    assert result["exact_match"] is False
    assert result["task_goal_met"] is False
    assert result["localization_f1"] == localization
    assert result["fault_type_f1"] == typing


def test_extra_hypothesis_penalizes_precision_and_goal() -> None:
    a = ("PE1", None, "bgp_neighbor_admin_down")
    b = ("PE2", None, "ospf_network_missing")
    result = score_structured_rca(_truth(a), _submission(a, b))
    assert result["rca_precision"] == 0.5
    assert result["rca_recall"] == 1.0
    assert result["rca_f1"] == 0.6667
    assert result["rca_accuracy"] == 1.0  # NIKA compatibility alias = recall
    assert result["task_goal_met"] is False
    assert result["tp"] == 1
    assert result["fp"] == 1
    assert result["fn"] == 0


def test_multiple_faults_and_missing_prediction() -> None:
    a = ("P1", "Loopback0", "loopback_admin_down")
    b = ("PE2", None, "bgp_neighbor_admin_down")
    result = score_structured_rca(_truth(a, b), _submission(a))
    assert result["rca_precision"] == 1
    assert result["rca_recall"] == 0.5
    assert result["false_negative"] == [
        {"resource_id": "node/pe2", "fault_type": "bgp_neighbor_admin_down"}
    ]


def test_no_submission_is_zero_not_keyword_pass() -> None:
    result = score_structured_rca(_truth(("P1", None, "ospf_network_missing")), None)
    assert result["status"] == "no_submission"
    assert result["rca_f1"] == 0
    assert result["task_goal_met"] is False


def test_invalid_submission_is_zero_and_does_not_crash() -> None:
    result = score_structured_rca(
        _truth(("P1", None, "ospf_network_missing")),
        {"is_anomaly": True, "root_causes": [{"fault_type": "ospf_network_missing"}]},
    )
    assert result["status"] == "invalid_submission"
    assert result["rca_f1"] == 0


def test_correct_rca_but_wrong_detection_is_not_goal_success() -> None:
    a = ("P1", "FastEthernet0/0", "link_down")
    result = score_structured_rca(_truth(a), _submission(a, anomaly=False))
    assert result["rca_f1"] == 1
    assert result["task_goal_met"] is False
    assert result["detection_score"] == 0


def test_no_ground_truth_raises_grading_error() -> None:
    with pytest.raises(ValueError, match="ground truth"):
        score_structured_rca([], _submission())


def test_fault_alias_and_node_scope_are_canonicalized_before_scoring() -> None:
    acl = score_structured_rca(
        _truth(("PE1", "FastEthernet4/0", "acl_traffic_block")),
        _submission(("PE1", "FastEthernet4/0", "acl_block")),
    )
    bgp = score_structured_rca(
        _truth(("CE-2A", None, "bgp_neighbor_admin_down")),
        _submission(
            ("CE-2A", "FastEthernet0/0", "bgp_neighbor_shutdown")
        ),
    )

    assert acl["task_goal_met"] is True
    assert bgp["task_goal_met"] is True
    assert bgp["predicted_root_causes"] == [
        {"resource_id": "node/ce-2a", "fault_type": "bgp_neighbor_admin_down"}
    ]
