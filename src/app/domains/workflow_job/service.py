"""Application service cho durable workflow queue."""

from datetime import UTC, datetime, timedelta

from app.domains.workflow_job.repository import WorkflowJobRepository
from app.domains.workflow_job.schemas import WorkflowJob, WorkflowJobStatus, WorkflowJobType


class WorkflowJobService:
    def __init__(
        self,
        repository: WorkflowJobRepository,
        *,
        max_attempts: int,
        retry_delay_seconds: float,
        lock_timeout_seconds: int,
    ) -> None:
        self._repository = repository
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._lock_timeout_seconds = lock_timeout_seconds

    def enqueue_message(
        self,
        conversation_id: str,
        message_id: str,
        *,
        benchmark_run_id: str | None = None,
        generate_title: bool = False,
    ) -> WorkflowJob:
        return self._repository.enqueue(
            WorkflowJobType.MESSAGE,
            f"message:{message_id}",
            {
                "conversation_id": conversation_id,
                "message_id": message_id,
                "benchmark_run_id": benchmark_run_id,
                "generate_title": generate_title,
            },
            max_attempts=self._max_attempts,
        )

    def enqueue_approval(self, operation_device_id: str) -> WorkflowJob:
        return self._repository.enqueue(
            WorkflowJobType.APPROVAL,
            f"approval:{operation_device_id}",
            {"operation_device_id": operation_device_id},
            max_attempts=self._max_attempts,
        )

    def claim_next(self, worker_id: str) -> WorkflowJob | None:
        return self._repository.claim_next(worker_id)

    def complete(self, job: WorkflowJob, worker_id: str) -> None:
        if not self._repository.complete(job.id, worker_id):
            raise RuntimeError("Không thể complete workflow job")

    def fail_or_retry(
        self,
        job: WorkflowJob,
        worker_id: str,
        error: Exception,
    ) -> WorkflowJobStatus:
        return self._repository.fail_or_retry(
            job,
            worker_id,
            str(error),
            retry_delay_seconds=self._retry_delay_seconds,
        )

    def recover_stale(self) -> int:
        return self._repository.recover_stale(
            datetime.now(UTC) - timedelta(seconds=self._lock_timeout_seconds)
        )
