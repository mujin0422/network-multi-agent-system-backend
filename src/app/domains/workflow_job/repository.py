"""PostgreSQL repository cho durable workflow queue."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.core.database import create_session_factory
from app.domains.workflow_job.models import WorkflowJobModel
from app.domains.workflow_job.schemas import WorkflowJob, WorkflowJobStatus, WorkflowJobType


class WorkflowJobRepository:
    def __init__(self, database_url: str) -> None:
        self._sessions = create_session_factory(database_url)

    def enqueue(
        self,
        job_type: WorkflowJobType,
        deduplication_key: str,
        payload: dict,
        *,
        max_attempts: int,
    ) -> WorkflowJob:
        """Tạo job idempotent theo deduplication key."""

        now = datetime.now(UTC)
        values = {
            "id": uuid4(),
            "job_type": job_type,
            "deduplication_key": deduplication_key,
            "payload": payload,
            "job_status": WorkflowJobStatus.PENDING,
            "attempts": 0,
            "max_attempts": max_attempts,
            "available_at": now,
            "created_at": now,
        }
        with self._sessions.begin() as session:
            model = session.scalars(
                insert(WorkflowJobModel)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["deduplication_key"])
                .returning(WorkflowJobModel)
            ).first()
            if model is None:
                model = session.scalar(
                    select(WorkflowJobModel).where(
                        WorkflowJobModel.deduplication_key == deduplication_key
                    )
                )
            if model is None:
                raise RuntimeError("Không thể enqueue workflow job")
            return WorkflowJob.model_validate(model, from_attributes=True)

    def claim_next(self, worker_id: str) -> WorkflowJob | None:
        """Claim đúng một PENDING job bằng FOR UPDATE SKIP LOCKED."""

        now = datetime.now(UTC)
        with self._sessions.begin() as session:
            model = session.scalar(
                select(WorkflowJobModel)
                .where(
                    WorkflowJobModel.job_status == WorkflowJobStatus.PENDING,
                    WorkflowJobModel.available_at <= now,
                    WorkflowJobModel.attempts < WorkflowJobModel.max_attempts,
                )
                .order_by(WorkflowJobModel.available_at, WorkflowJobModel.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if model is None:
                return None
            model.job_status = WorkflowJobStatus.RUNNING
            model.attempts += 1
            model.locked_at = now
            model.locked_by = worker_id
            session.flush()
            return WorkflowJob.model_validate(model, from_attributes=True)

    def complete(self, job_id: UUID, worker_id: str) -> bool:
        """Đánh dấu COMPLETED nếu job vẫn thuộc worker hiện tại."""

        with self._sessions.begin() as session:
            result = session.execute(
                update(WorkflowJobModel)
                .where(
                    WorkflowJobModel.id == job_id,
                    WorkflowJobModel.job_status == WorkflowJobStatus.RUNNING,
                    WorkflowJobModel.locked_by == worker_id,
                )
                .values(
                    job_status=WorkflowJobStatus.COMPLETED,
                    locked_at=None,
                    locked_by=None,
                    completed_at=datetime.now(UTC),
                )
            )
            return bool(result.rowcount)

    def fail_or_retry(
        self,
        job: WorkflowJob,
        worker_id: str,
        error: str,
        *,
        retry_delay_seconds: float,
    ) -> WorkflowJobStatus:
        """Retry có delay hoặc chốt FAILED khi đã hết số lần thử."""

        now = datetime.now(UTC)
        exhausted = job.attempts >= job.max_attempts
        next_status = WorkflowJobStatus.FAILED if exhausted else WorkflowJobStatus.PENDING
        with self._sessions.begin() as session:
            result = session.execute(
                update(WorkflowJobModel)
                .where(
                    WorkflowJobModel.id == job.id,
                    WorkflowJobModel.job_status == WorkflowJobStatus.RUNNING,
                    WorkflowJobModel.locked_by == worker_id,
                )
                .values(
                    job_status=next_status,
                    available_at=now + timedelta(seconds=retry_delay_seconds),
                    locked_at=None,
                    locked_by=None,
                    last_error=error[:8000],
                    completed_at=now if exhausted else None,
                )
            )
            if not result.rowcount:
                raise RuntimeError("Workflow job không còn thuộc worker hiện tại")
        return next_status

    def recover_stale(self, locked_before: datetime) -> int:
        """Đưa job RUNNING của worker chết về PENDING hoặc FAILED."""

        with self._sessions.begin() as session:
            models = list(
                session.scalars(
                    select(WorkflowJobModel)
                    .where(
                        WorkflowJobModel.job_status == WorkflowJobStatus.RUNNING,
                        or_(
                            WorkflowJobModel.locked_at.is_(None),
                            WorkflowJobModel.locked_at < locked_before,
                        ),
                    )
                    .with_for_update(skip_locked=True)
                ).all()
            )
            now = datetime.now(UTC)
            for model in models:
                exhausted = model.attempts >= model.max_attempts
                model.job_status = (
                    WorkflowJobStatus.FAILED if exhausted else WorkflowJobStatus.PENDING
                )
                model.locked_at = None
                model.locked_by = None
                model.last_error = "Worker lock hết hạn"
                model.completed_at = now if exhausted else None
            return len(models)
