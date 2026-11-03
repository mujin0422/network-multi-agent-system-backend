"""Các hàm xây dựng kết quả đánh giá cho một benchmark run."""

from datetime import datetime
from uuid import uuid4

from app.domains.benchmark.schemas import BenchmarkRunRecord
from app.domains.benchmark.schemas.benchmark_observation import BenchmarkObservation
from app.domains.benchmark.utils.active_runtime import active_workflow_duration_ms
from app.domains.conversation.schemas import Message
from app.domains.evaluation.schemas import (
    EvaluationMetricType,
    EvaluationResult,
    EvaluationStatus,
    EvaluatorType,
    TaskEvaluationDetail,
    TaskEvaluationMetric,
)
from app.domains.execution.schemas import TaskDetail


def build_benchmark_evaluation(
    run: BenchmarkRunRecord,
    task: TaskDetail,
    response: Message | None,
    evaluated_at: datetime,
    observations: BenchmarkObservation | None = None,
) -> tuple[TaskEvaluationDetail, EvaluationResult]:
    """Tạo evaluation và kết quả RCA từ response của Agent."""

    observations = observations or BenchmarkObservation()
    response_at = response.created_at if response is not None else None
    active_ms, approval_wait_ms = (
        active_workflow_duration_ms(task.created_at, response_at, observations)
        if response_at is not None
        else (None, None)
    )

    # Count persisted agent-tool calls, not User/Agent chat messages or chain steps.
    interaction_turns = observations.agent_tool_calls
    response_text = response.message if response else ""
    normalized_response = response_text.casefold()
    required_terms = run.scenario_snapshot.evaluation_required_terms
    missing_terms = [
        term
        for term in required_terms
        if term.casefold() not in normalized_response
    ]
    matched_terms = [
        term
        for term in required_terms
        if term.casefold() in normalized_response
    ]
    rca_result = (
        EvaluationResult.PASS if not missing_terms else EvaluationResult.FAIL
    )
    goal_result = (
        EvaluationResult.PASS
        if response is not None and rca_result == EvaluationResult.PASS
        else EvaluationResult.FAIL
    )
    evaluation_id = uuid4()
    evidence = {
        "benchmark_run_id": run.id,
        "scenario_id": run.scenario_id,
        "scenario_version": run.scenario_version,
        "missing_terms": missing_terms,
    }
    evaluation = TaskEvaluationDetail(
        id=evaluation_id,
        task_id=task.id,
        evaluation_status=EvaluationStatus.COMPLETED,
        evaluator_type=EvaluatorType.AUTOMATED,
        evaluator_version="db-benchmark-v3",
        created_at=evaluated_at,
        evaluated_at=evaluated_at,
        metrics=[
            TaskEvaluationMetric(
                id=uuid4(),
                evaluation_id=evaluation_id,
                metric_type=EvaluationMetricType.GOAL,
                result=goal_result,
                is_required=True,
                expected_value={"required_terms": required_terms},
                actual_value={"final_response": response_text},
                evidence=evidence,
                created_at=evaluated_at,
            ),
            TaskEvaluationMetric(
                id=uuid4(),
                evaluation_id=evaluation_id,
                metric_type=EvaluationMetricType.RCA,
                result=rca_result,
                is_required=True,
                expected_value=[
                    item.model_dump()
                    for item in run.scenario_snapshot.ground_truth
                ],
                actual_value={"matched_terms": matched_terms},
                evidence=evidence,
                created_at=evaluated_at,
            ),
            TaskEvaluationMetric(
                id=uuid4(),
                evaluation_id=evaluation_id,
                metric_type=EvaluationMetricType.REMEDIATION,
                result=EvaluationResult.NOT_APPLICABLE,
                is_required=False,
                was_attempted=False,
                evidence=evidence,
                created_at=evaluated_at,
            ),
            TaskEvaluationMetric(
                id=uuid4(),
                evaluation_id=evaluation_id,
                metric_type=EvaluationMetricType.SAFETY,
                result=EvaluationResult.NOT_APPLICABLE,
                is_required=False,
                evidence=evidence,
                created_at=evaluated_at,
            ),
            TaskEvaluationMetric(
                id=uuid4(),
                evaluation_id=evaluation_id,
                metric_type=EvaluationMetricType.LATENCY,
                # A duration is an observation; no arbitrary PASS/FAIL threshold.
                result=EvaluationResult.UNKNOWN,
                is_required=False,
                actual_value={"active_duration_ms": active_ms} if active_ms is not None else None,
                evidence={
                    "definition": (
                        "AI workflow lifetime: Task created to FINAL_RESPONSE, "
                        "minus human approval waiting; includes Planner, Network "
                        "Agent, Analyst and orchestration overhead"
                    ),
                    "task_created_at": task.created_at.isoformat(),
                    "final_response_created_at": response_at.isoformat() if response_at else None,
                    "approval_wait_ms": approval_wait_ms,
                    "approval_pause_count": len(observations.approval_wait_intervals),
                    "approval_wait_incomplete": observations.approval_wait_open,
                    "excludes_human_approval_wait": True,
                    "excludes_gns3_preparation": True,
                    "model_only_inference_time": False,
                },
                created_at=evaluated_at,
            ),
            TaskEvaluationMetric(
                id=uuid4(),
                evaluation_id=evaluation_id,
                metric_type=EvaluationMetricType.INTERACTION_TURNS,
                # Count only: there is no declared success threshold for turns.
                result=EvaluationResult.UNKNOWN,
                is_required=False,
                actual_value={"count": interaction_turns} if interaction_turns is not None else None,
                evidence={
                    "definition": "count of task_executions with non-null tool_name for this task",
                    "scope": "agent-to-tool calls",
                    "excludes": ["benchmark fault injection", "benchmark cleanup", "chat message count"],
                },
                created_at=evaluated_at,
            ),
        ],
    )
    return evaluation, rca_result
