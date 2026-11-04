"""NIKA 0.2-inspired set scoring for (resource_id, fault_type) diagnoses.

This is deterministic scoring of an *agent-generated* structured submission;
the grader never sends a run's ground truth or required keyword terms to the
Analyst Agent. NIKA 0.2 uses RCA precision/recall/F1 over pair sets and
separate localization and fault-type scores. Here Cisco interfaces may contain
slashes, so we retain the complete ifName in the resource key.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.domains.evaluation.schemas.diagnosis import PredictedRootCause
from app.domains.evaluation.schemas.diagnosis import canonical_fault_type
from app.domains.benchmark.schemas.common import BenchmarkRootCause


def resource_id(device: str, interface: str | None) -> str:
    """Canonical node/interface identifier, compatible with NIKA's resource concept."""
    host = device.strip().casefold()
    if interface and interface.strip():
        return f"interface/{host}/{interface.strip().casefold()}"
    return f"node/{host}"


def _pair(cause: BenchmarkRootCause | PredictedRootCause) -> tuple[str, str]:
    return (
        resource_id(cause.device, cause.interface),
        canonical_fault_type(cause.fault_type).value,
    )


def _prf(predicted: set, truth: set) -> dict[str, float]:
    """Precision/recall/F1; NIKA's *_accuracy is a recall compatibility alias."""
    if not predicted and not truth:
        return {"accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0}
    tp = len(predicted & truth)
    fp = len(predicted - truth)
    fn = len(truth - predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "accuracy": round(recall, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def _serialize(pairs: set[tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {"resource_id": resource, "fault_type": fault}
        for resource, fault in sorted(pairs)
    ]


def score_structured_rca(
    ground_truth: list[BenchmarkRootCause],
    submission: dict[str, Any] | None,
) -> dict[str, Any]:
    """Score independent detection, localization, fault-type and joint RCA.

    Invalid / missing agent submissions score zero, as in NIKA. A corrupt
    ground-truth object raises instead of silently fabricating a FAIL.
    """
    # Bước 1: Từ chối chấm khi benchmark không có Ground Truth hợp lệ.
    if not ground_truth:
        raise ValueError("Cannot grade structured RCA without ground truth")

    # Bước 2: Chuẩn hóa Ground Truth thành tập (resource_id, fault_type).
    truth_pairs = {_pair(item) for item in ground_truth}
    status = "scored"
    anomaly: bool | None = None
    predicted_causes: list[PredictedRootCause] = []

    # Bước 3: Validate structured submission độc lập do Analyst tạo ra.
    if submission is None:
        status = "no_submission"
    elif not isinstance(submission, dict):
        status = "invalid_submission"
    else:
        try:
            raw_causes = submission.get("root_causes")
            if not isinstance(raw_causes, list):
                raise ValueError("root_causes must be a list")
            predicted_causes = [PredictedRootCause.model_validate(item) for item in raw_causes]
            raw_anomaly = submission.get("is_anomaly")
            if isinstance(raw_anomaly, bool):
                anomaly = raw_anomaly
            # Missing/invalid anomaly is scored as detection=0 but need not
            # discard an otherwise valid structured RCA list.
        except (ValueError, ValidationError, TypeError):
            predicted_causes = []
            anomaly = None
            status = "invalid_submission"

    # Bước 4: Chuẩn hóa alias và phạm vi node/interface của dự đoán.
    pred_pairs = {_pair(item) for item in predicted_causes}
    truth_resources = {resource for resource, _ in truth_pairs}
    pred_resources = {resource for resource, _ in pred_pairs}
    truth_types = {fault for _, fault in truth_pairs}
    pred_types = {fault for _, fault in pred_pairs}

    # Bước 5: Tính riêng joint RCA, localization và fault-type PRF.
    joint = _prf(pred_pairs, truth_pairs)
    localization = _prf(pred_resources, truth_resources)
    fault_types = _prf(pred_types, truth_types)
    # Current diagnosis scenarios explicitly inject a fault, so GT anomaly=True.
    detection_score = 1.0 if anomaly is True else 0.0
    # Bước 6: GOAL chỉ PASS khi detection đúng và tập nguyên nhân khớp hoàn toàn.
    exact_match = bool(pred_pairs == truth_pairs)
    task_goal_met = bool(exact_match and detection_score == 1.0)
    return {
        "status": status,
        "is_anomaly": anomaly,
        "detection_score": detection_score,
        "rca_accuracy": joint["accuracy"],
        "rca_precision": joint["precision"],
        "rca_recall": joint["recall"],
        "rca_f1": joint["f1"],
        "localization_accuracy": localization["accuracy"],
        "localization_precision": localization["precision"],
        "localization_recall": localization["recall"],
        "localization_f1": localization["f1"],
        "fault_type_precision": fault_types["precision"],
        "fault_type_recall": fault_types["recall"],
        "fault_type_f1": fault_types["f1"],
        "exact_match": exact_match,
        "task_goal_met": task_goal_met,
        "predicted_root_causes": _serialize(pred_pairs),
        "expected_root_causes": _serialize(truth_pairs),
        "true_positive": _serialize(pred_pairs & truth_pairs),
        "false_positive": _serialize(pred_pairs - truth_pairs),
        "false_negative": _serialize(truth_pairs - pred_pairs),
        "tp": len(pred_pairs & truth_pairs),
        "fp": len(pred_pairs - truth_pairs),
        "fn": len(truth_pairs - pred_pairs),
        "scoring_method": "nika-0.2-inspired-canonical-set-pair-prf-v2",
    }
