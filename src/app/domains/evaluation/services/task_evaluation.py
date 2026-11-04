"""Nghiệp vụ truy vấn và lưu kết quả đánh giá Task."""

from collections import defaultdict
from uuid import UUID

from app.domains.evaluation.repositories import (
    TaskEvaluationMetricRepository,
    TaskEvaluationRepository,
)
from app.domains.evaluation.schemas import (
    EvaluationMetricType,
    TaskEvaluation,
    TaskEvaluationDetail,
    TaskEvaluationMetric,
    TaskEvaluationSummary,
)


class TaskEvaluationService:
    def __init__(
        self,
        evaluation_repository: TaskEvaluationRepository,
        metric_repository: TaskEvaluationMetricRepository,
    ) -> None:
        """Khởi tạo service cùng các repository của Evaluation."""

        self._evaluations = evaluation_repository
        self._metrics = metric_repository

    def save(self, evaluation: TaskEvaluationDetail) -> None:
        """Lưu Evaluation trước, sau đó lưu toàn bộ metric liên quan."""

        self._evaluations.save(evaluation)
        self._metrics.save(evaluation.metrics)

    def get_by_id(self, evaluation_id: UUID) -> TaskEvaluationDetail | None:
        """Lấy Evaluation cùng toàn bộ metric theo ID."""

        return self._to_detail(self._evaluations.get_by_id(evaluation_id))

    def get_by_task_id(self, task_id: str) -> TaskEvaluationDetail | None:
        """Lấy Evaluation cùng toàn bộ metric theo Task ID."""

        return self._to_detail(self._evaluations.get_by_task_id(task_id))

    def get_recent(self, limit: int = 50) -> list[TaskEvaluationSummary]:
        """Tổng hợp history an toàn, không trả expected value hoặc evidence."""

        evaluations = self._evaluations.get_recent(limit)
        metrics = self._metrics.get_all_by_evaluation_ids(
            evaluation.id for evaluation in evaluations
        )
        metrics_by_evaluation: dict[UUID, list[TaskEvaluationMetric]] = defaultdict(list)
        for metric in metrics:
            metrics_by_evaluation[metric.evaluation_id].append(metric)
        return [
            self._to_summary(
                evaluation,
                metrics_by_evaluation[evaluation.id],
            )
            for evaluation in evaluations
        ]

    def _to_detail(
        self,
        evaluation: TaskEvaluation | None,
    ) -> TaskEvaluationDetail | None:
        """Kết hợp Evaluation với danh sách metric thành schema chi tiết."""

        if evaluation is None:
            return None
        return TaskEvaluationDetail(
            **evaluation.model_dump(),
            metrics=self._metrics.get_all_by_evaluation_id(evaluation.id),
        )

    @staticmethod
    def _to_summary(
        evaluation: TaskEvaluation,
        metrics: list[TaskEvaluationMetric],
    ) -> TaskEvaluationSummary:
        """Tổng hợp metric thành dữ liệu history an toàn cho giao diện."""

        results = {metric.metric_type: metric.result for metric in metrics}
        measurements = {}
        scores = {}
        for metric in metrics:
            actual = metric.actual_value
            if (
                metric.metric_type == EvaluationMetricType.RCA
                and evaluation.evaluator_version
                in {"db-benchmark-v4", "db-benchmark-v5"}
                and isinstance(actual, dict)
            ):
                for field in (
                    "rca_f1",
                    "localization_f1",
                    "fault_type_f1",
                    "rca_precision",
                    "rca_recall",
                ):
                    value = actual.get(field)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        scores[field] = float(value)
            measurement_key = None
            if metric.metric_type == EvaluationMetricType.LATENCY:
                measurement_key = (
                    "active_duration_ms"
                    if evaluation.evaluator_version
                    in {"db-benchmark-v3", "db-benchmark-v4", "db-benchmark-v5"}
                    else "duration_ms"
                )
            elif metric.metric_type == EvaluationMetricType.INTERACTION_TURNS:
                measurement_key = "count"
            if measurement_key and isinstance(actual, dict):
                value = actual.get(measurement_key)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    measurements[metric.metric_type] = value
        return TaskEvaluationSummary(
            **evaluation.model_dump(),
            results=results,
            measurements=measurements,
            scores=scores,
        )
