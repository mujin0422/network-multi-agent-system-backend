"""Standalone worker xử lý LangGraph jobs ngoài tiến trình HTTP request."""

import asyncio
import logging
import os
import socket

from app.agents.dependencies import _build_network_automation_workflow
from app.core.config import get_settings
from app.domains.benchmark.routers.dependencies import _build_benchmark_run_service
from app.domains.conversation.repositories import ConversationRepository, MessageRepository
from app.domains.conversation.routers.dependencies import (
    _build_conversation_service,
    _build_conversation_title_generator,
)
from app.domains.conversation.schemas import MessageType
from app.domains.workflow_job.dependencies import build_workflow_job_service
from app.domains.workflow_job.schemas import WorkflowJob, WorkflowJobStatus, WorkflowJobType


logger = logging.getLogger(__name__)


class WorkflowJobProcessor:
    """Dựng lại aggregate từ ID trong job và gọi workflow tương ứng."""

    def __init__(self) -> None:
        settings = get_settings()
        self._conversations = ConversationRepository(settings.database_url)
        self._messages = MessageRepository(settings.database_url)
        self._conversation_service = _build_conversation_service()
        self._title_generator = _build_conversation_title_generator()
        self._workflow = _build_network_automation_workflow()
        self._benchmark_service = _build_benchmark_run_service()

    async def process(self, job: WorkflowJob) -> None:
        if job.job_type == WorkflowJobType.MESSAGE:
            await self._process_message(job)
            return
        if job.job_type == WorkflowJobType.APPROVAL:
            await self._process_approval(job)
            return
        raise ValueError(f"Workflow job type không được hỗ trợ: {job.job_type}")

    async def _process_message(self, job: WorkflowJob) -> None:
        conversation_id = str(job.payload["conversation_id"])
        message_id = str(job.payload["message_id"])
        conversation = self._conversations.get_by_id(conversation_id)
        message = self._messages.get_by_id(message_id)
        if conversation is None or message is None:
            raise RuntimeError("Conversation hoặc Message của workflow job không tồn tại")

        state = await self._workflow.run_message(conversation, message)
        benchmark_run_id = job.payload.get("benchmark_run_id")
        if benchmark_run_id is not None:
            task = state.get("task")
            if task is None:
                raise RuntimeError("Workflow benchmark không trả về Task")
            response = state.get("response")
            if response is not None and response.message_type == MessageType.FINAL_RESPONSE:
                self._benchmark_service.complete(str(benchmark_run_id), task, response)

        if bool(job.payload.get("generate_title")):
            try:
                title = await self._title_generator.generate(message.message)
                self._conversation_service.update_title(conversation, title)
            except Exception:
                logger.exception("Không thể tạo title cho conversation %s", conversation.id)

    async def _process_approval(self, job: WorkflowJob) -> None:
        operation_device_id = str(job.payload["operation_device_id"])
        state = await self._workflow.resume_after_approval(operation_device_id)
        task = state.get("task")
        if task is not None:
            self._benchmark_service.complete_for_task(task, state.get("response"))

    def handle_permanent_failure(self, job: WorkflowJob, error: Exception) -> None:
        """Đồng bộ benchmark FAILED chỉ sau khi queue đã hết retry."""

        benchmark_run_id = job.payload.get("benchmark_run_id")
        if job.job_type == WorkflowJobType.MESSAGE and benchmark_run_id is not None:
            self._benchmark_service.fail(str(benchmark_run_id), error)


async def run_workflow_worker() -> None:
    """Claim và xử lý job liên tục; mỗi job được chốt qua worker ownership."""

    settings = get_settings()
    service = build_workflow_job_service()
    processor = WorkflowJobProcessor()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    recovered = await asyncio.to_thread(service.recover_stale)
    logger.info("WORKFLOW_WORKER_STARTED | worker_id=%s recovered=%s", worker_id, recovered)

    while True:
        job = await asyncio.to_thread(service.claim_next, worker_id)
        if job is None:
            await asyncio.sleep(settings.workflow_job_poll_interval_seconds)
            continue
        logger.info(
            "WORKFLOW_JOB_STARTED | worker_id=%s job_id=%s type=%s attempt=%s",
            worker_id,
            job.id,
            job.job_type,
            job.attempts,
        )
        try:
            await processor.process(job)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            status = await asyncio.to_thread(
                service.fail_or_retry,
                job,
                worker_id,
                error,
            )
            logger.exception(
                "WORKFLOW_JOB_ERROR | worker_id=%s job_id=%s status=%s",
                worker_id,
                job.id,
                status,
            )
            if status == WorkflowJobStatus.FAILED:
                await asyncio.to_thread(processor.handle_permanent_failure, job, error)
            continue
        await asyncio.to_thread(service.complete, job, worker_id)
        logger.info(
            "WORKFLOW_JOB_COMPLETED | worker_id=%s job_id=%s",
            worker_id,
            job.id,
        )
