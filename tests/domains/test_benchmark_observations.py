"""Quantitative benchmark metrics: no arbitrary PASS/FAIL thresholds."""

from datetime import UTC, datetime, timedelta

from app.domains.benchmark.schemas import BenchmarkRunRecord, BenchmarkScenario
from app.domains.benchmark.schemas.benchmark_observation import ApprovalWaitInterval, BenchmarkObservation
from app.domains.benchmark.repositories.benchmark_observation import approval_pauses_from_events
from app.domains.execution.schemas import ActivityEventType
from app.domains.benchmark.utils import build_benchmark_evaluation
from app.domains.conversation.schemas import Message, MessageSender, MessageType
from app.domains.evaluation.schemas import EvaluationMetricType, EvaluationResult
from app.domains.execution.schemas import TaskDetail, TaskStatus, TaskType


def make_evaluation(observation: BenchmarkObservation, response_time: datetime, *, task_created_at: datetime | None = None):
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
        "created_at": task_created_at or source,
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
    assert metrics[EvaluationMetricType.LATENCY].actual_value == {"active_duration_ms": 4250}
    assert metrics[EvaluationMetricType.INTERACTION_TURNS].actual_value == {"count": 3}
    assert metrics[EvaluationMetricType.LATENCY].result == EvaluationResult.UNKNOWN
    assert metrics[EvaluationMetricType.INTERACTION_TURNS].result == EvaluationResult.UNKNOWN
    assert metrics[EvaluationMetricType.RCA].result == EvaluationResult.PASS
    assert metrics[EvaluationMetricType.GOAL].result == EvaluationResult.PASS
    assert metrics[EvaluationMetricType.REMEDIATION].result == EvaluationResult.NOT_APPLICABLE
    assert metrics[EvaluationMetricType.SAFETY].result == EvaluationResult.NOT_APPLICABLE


def test_missing_request_timestamp_does_not_break_task_based_measurement() -> None:
    now = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    metrics = make_evaluation(BenchmarkObservation(agent_tool_calls=0), now)
    assert metrics[EvaluationMetricType.LATENCY].actual_value == {"active_duration_ms": 0}
    assert metrics[EvaluationMetricType.INTERACTION_TURNS].actual_value == {"count": 0}


def test_negative_duration_is_unknown_instead_of_clamped_to_zero() -> None:
    now = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    metrics = make_evaluation(
        BenchmarkObservation(agent_tool_calls=1),
        now,
        task_created_at=now + timedelta(seconds=10),
    )
    assert metrics[EvaluationMetricType.LATENCY].actual_value is None


def test_ai_runtime_excludes_human_wait_and_preserves_tool_calls() -> None:
    start = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    metrics = make_evaluation(
        BenchmarkObservation(
            agent_tool_calls=4,
            approval_wait_intervals=[
                ApprovalWaitInterval(
                    started_at=start + timedelta(seconds=10),
                    resumed_at=start + timedelta(seconds=35),
                ),
            ],
        ),
        start + timedelta(seconds=45),
    )
    assert metrics[EvaluationMetricType.LATENCY].actual_value == {"active_duration_ms": 20000}
    assert metrics[EvaluationMetricType.LATENCY].evidence["approval_wait_ms"] == 25000
    assert metrics[EvaluationMetricType.INTERACTION_TURNS].actual_value == {"count": 4}


def test_unfinished_approval_pause_yields_missing_measurement() -> None:
    start = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    metrics = make_evaluation(
        BenchmarkObservation(approval_wait_open=True),
        start + timedelta(seconds=40),
    )
    assert metrics[EvaluationMetricType.LATENCY].actual_value is None


def test_waiting_events_pair_with_actual_execution_resume() -> None:
    start = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    pauses, open_wait = approval_pauses_from_events([
        (ActivityEventType.EXECUTION_STARTED, start + timedelta(seconds=1)),
        (ActivityEventType.APPROVAL_REQUESTED, start + timedelta(seconds=5)),
        (ActivityEventType.APPROVAL_APPROVED, start + timedelta(seconds=25)),
        (ActivityEventType.EXECUTION_STARTED, start + timedelta(seconds=27)),
    ])
    assert not open_wait
    assert pauses[0].started_at == start + timedelta(seconds=5)
    assert pauses[0].resumed_at == start + timedelta(seconds=27)


def test_waiting_events_refuse_unmatched_request() -> None:
    start = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    pauses, open_wait = approval_pauses_from_events([
        (ActivityEventType.APPROVAL_REQUESTED, start),
        (ActivityEventType.APPROVAL_APPROVED, start + timedelta(seconds=2)),
    ])
    assert open_wait
    assert pauses == []


def test_overlapping_approval_waits_are_merged() -> None:
    from app.domains.benchmark.utils.active_runtime import active_workflow_duration_ms
    start = datetime(2026, 11, 3, 8, 0, tzinfo=UTC)
    ms, wait_ms = active_workflow_duration_ms(
        start, start + timedelta(seconds=50),
        BenchmarkObservation(approval_wait_intervals=[
            ApprovalWaitInterval(
                started_at=start + timedelta(seconds=10),
                resumed_at=start + timedelta(seconds=30),
            ),
            ApprovalWaitInterval(
                started_at=start + timedelta(seconds=20),
                resumed_at=start + timedelta(seconds=40),
            ),
        ]),
    )
    assert ms == 20000
    assert wait_ms == 30000
