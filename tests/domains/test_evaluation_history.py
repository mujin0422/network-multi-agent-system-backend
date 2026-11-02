"""Evaluation history is safe to show without benchmark ground truth."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from app.domains.evaluation.routers.task_evaluation import list_evaluations
from app.domains.evaluation.schemas import (
    EvaluationMetricType,
    EvaluationResult,
    EvaluationStatus,
    EvaluatorType,
    TaskEvaluationSummary,
)


class FakeEvaluationRepository:
    def __init__(self) -> None:
        self.last_limit: int | None = None

    def get_recent(self, limit: int = 50) -> list[TaskEvaluationSummary]:
        self.last_limit = limit
        now = datetime.now(UTC)
        return [
            TaskEvaluationSummary(
                id=uuid4(),
                task_id="task-123",
                evaluation_status=EvaluationStatus.COMPLETED,
                evaluator_type=EvaluatorType.AUTOMATED,
                evaluator_version="db-benchmark-v1",
                created_at=now,
                evaluated_at=now,
                results={
                    EvaluationMetricType.GOAL: EvaluationResult.PASS,
                    EvaluationMetricType.RCA: EvaluationResult.FAIL,
                    EvaluationMetricType.REMEDIATION: EvaluationResult.NOT_APPLICABLE,
                    EvaluationMetricType.SAFETY: EvaluationResult.NOT_APPLICABLE,
                },
            )
        ]


def test_history_returns_metric_statuses_without_ground_truth() -> None:
    repository = FakeEvaluationRepository()

    rows = asyncio.run(
        list_evaluations(
            _user=None,  # Auth is checked by FastAPI's dependency layer.
            evaluation_repository=repository,  # type: ignore[arg-type]
            limit=25,
        )
    )

    assert repository.last_limit == 25
    assert len(rows) == 1
    assert rows[0].results[EvaluationMetricType.RCA] == EvaluationResult.FAIL
    serialized = rows[0].model_dump(mode="json")
    assert "results" in serialized
    assert "metrics" not in serialized
    assert "expected_value" not in serialized
    assert "actual_value" not in serialized
    assert "evidence" not in serialized
