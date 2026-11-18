"""Unit tests cho durable workflow queue application service."""

from datetime import UTC, datetime
from uuid import uuid4

from app.domains.workflow_job.schemas import WorkflowJob, WorkflowJobStatus, WorkflowJobType
from app.domains.workflow_job.service import WorkflowJobService


class WorkflowJobRepositoryStub:
    def __init__(self) -> None:
        self.enqueued: list[tuple] = []

    def enqueue(self, job_type, key, payload, *, max_attempts):
        self.enqueued.append((job_type, key, payload, max_attempts))
        now = datetime.now(UTC)
        return WorkflowJob(
            id=uuid4(),
            job_type=job_type,
            deduplication_key=key,
            payload=payload,
            job_status=WorkflowJobStatus.PENDING,
            attempts=0,
            max_attempts=max_attempts,
            available_at=now,
            created_at=now,
        )


def build_service(repository: WorkflowJobRepositoryStub) -> WorkflowJobService:
    return WorkflowJobService(
        repository,
        max_attempts=3,
        retry_delay_seconds=5,
        lock_timeout_seconds=900,
    )


def test_message_job_is_deduplicated_by_source_message() -> None:
    repository = WorkflowJobRepositoryStub()
    service = build_service(repository)

    job = service.enqueue_message(
        "cons-test",
        "mesg-test",
        benchmark_run_id="benr-test",
        generate_title=True,
    )

    assert job.job_type == WorkflowJobType.MESSAGE
    assert repository.enqueued == [
        (
            WorkflowJobType.MESSAGE,
            "message:mesg-test",
            {
                "conversation_id": "cons-test",
                "message_id": "mesg-test",
                "benchmark_run_id": "benr-test",
                "generate_title": True,
            },
            3,
        )
    ]


def test_approval_job_is_deduplicated_by_operation_device() -> None:
    repository = WorkflowJobRepositoryStub()
    service = build_service(repository)

    job = service.enqueue_approval("opdv-test")

    assert job.job_type == WorkflowJobType.APPROVAL
    assert repository.enqueued[0][1] == "approval:opdv-test"
    assert repository.enqueued[0][2] == {"operation_device_id": "opdv-test"}
