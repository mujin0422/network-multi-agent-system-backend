"""Quantitative benchmark metrics: no arbitrary PASS/FAIL thresholds."""

from datetime import UTC, datetime, timedelta

from app.domains.benchmark.schemas import BenchmarkRunRecord, BenchmarkScenario
from app.domains.benchmark.schemas.benchmark_observation import BenchmarkObservation
from app.domains.benchmark.utils import build_benchmark_evaluation
from app.domains.conversation.schemas import Message, MessageSender, MessageType
from app.domains.evaluation.schemas import EvaluationMetricType, EvaluationResult
from app.domains.execution.schemas import TaskDetail, TaskStatus, TaskType


def make_evaluation(observation: BenchmarkObservation, response_time: datetime):
    source = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    scenario = BenchmarkScenario.model_validate({
        "scenario_key": "latency-test",
        "version": "1.0",
        "name": "Test latency",
        "description": "Test latency and interaction turns",
        "topology": "mpls-core",
        "initial_message": "Diagnose",
        "preconditions": [],
        "injection": [{"device": "P1", "action": "interface_shutdown", "interface": "FastEthernet0/0"}],
        "fault_verification": [{"device": "P1", "command": "show interfaces", "assertion": {"contains": "down"}}],
        "ground_truth": [{"fault_type": "link_down", "device": "P1"}],
        "evaluation_required_terms": ["P1", "shutdown"],
        "cleanup": [{"device": "P1", "action": "interface_no_shutdown", "interface": "FastEthernet0/0"}],
    })
    run = BenchmarkRunRecord.model_validate({
        "id": "benr-031126-1234abcd",
        "scenario_id": "benc-031126-1234abcd",
        "scenario_version": "1.0",
        "scenario_name": "Test latency",
        "status": "RUNNING",
        "started_by": "test-user",
        "initial_message": "Diagnose",
        "source_message_id": "mesg-request",
        "started_at": source - timedelta(minutes=2),
        "scenario_snapshot": scenario.model_dump(),
    })
    task = TaskDetail.model_validate({
        "id": "task-test",
        "conversation_id": "conv-test",
        "source_message_id": "mesg-request",
        "user_id": "test-user",
        "input_message": "Diagnose",
        "task_status": TaskStatus.SUCCESS,
        "task_type": TaskType.DIAGNOSIS,
        "created_at": source,
    })
    response = Message.model_validate({
        "id": "mesg-response",
        "conversation_id": "conv-test",
        "reply_to_message_id": "mesg-request",
        "sender_by": MessageSender.AGENT,
        "message_type": MessageType.FINAL_RESPONSE,
        "message": "P1 interface shutdown",
        "created_at": response_time,
    })
    evaluation, _ = build_benchmark_evaluation(
        run, task, response, response_time, observations=observation
    )
    return {metric.metric_type: metric for metric in evaluation.metrics}


def test_latency_excludes_gns3_setup_and_counts_agent_tool_calls() -> None:
    start = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    metrics = make_evaluation(
        BenchmarkObservation(
            source_message_created_at=start,
            agent_tool_calls=3,
        ),
        start + timedelta(seconds=4, milliseconds=250),
    )
    assert len(metrics) == 6
    assert metrics[EvaluationMetricType.LATENCY].actual_value == {"duration_ms": 4250}
    assert metrics[EvaluationMetricType.INTERACTION_TURNS].actual_value == {"count": 3}
    assert metrics[EvaluationMetricType.LATENCY].result == EvaluationResult.UNKNOWN
    assert metrics[EvaluationMetricType.INTERACTION_TURNS].result == EvaluationResult.UNKNOWN
    assert metrics[EvaluationMetricType.RCA].result == EvaluationResult.PASS
    assert metrics[EvaluationMetricType.GOAL].result == EvaluationResult.PASS
    assert metrics[EvaluationMetricType.REMEDIATION].result == EvaluationResult.NOT_APPLICABLE
    assert metrics[EvaluationMetricType.SAFETY].result == EvaluationResult.NOT_APPLICABLE


def test_missing_request_timestamp_does_not_invent_latency() -> None:
    now = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    metrics = make_evaluation(BenchmarkObservation(agent_tool_calls=0), now)
    assert metrics[EvaluationMetricType.LATENCY].actual_value is None
    assert metrics[EvaluationMetricType.INTERACTION_TURNS].actual_value == {"count": 0}


def test_negative_duration_is_unknown_instead_of_clamped_to_zero() -> None:
    now = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    metrics = make_evaluation(
        BenchmarkObservation(
            source_message_created_at=now + timedelta(seconds=10),
            agent_tool_calls=1,
        ),
        now,
    )
    assert metrics[EvaluationMetricType.LATENCY].actual_value is None
