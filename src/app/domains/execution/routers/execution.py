"""HTTP routes của AI Execution Management domain."""

import asyncio
import logging
from time import monotonic
from typing import Annotated, AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from app.agents.dependencies import get_network_automation_workflow
from app.core.pagination import PageResponse
from app.agents.workflow import NetworkAutomationWorkflow
from app.domains.benchmark.routers.dependencies import get_benchmark_run_service
from app.domains.benchmark.services import BenchmarkRunService
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User

from app.domains.execution.schemas import (
    DeviceActionLog,
    Operation,
    ActivityActorType,
    ActivityEventType,
    OperationCreate,
    OperationDeviceApprovalDecision,
    OperationDeviceApprovalResponse,
    Task,
    TaskActivityEvent,
    TaskCreate,
    TaskDetail,
    TaskRecords,
    TaskStreamEvent,
)
from app.domains.execution.services import ExecutionService
from app.domains.execution.routers.dependencies import get_execution_service


router = APIRouter()
operations_router = APIRouter()
approvals_router = APIRouter()
device_action_logs_router = APIRouter()
logger = logging.getLogger(__name__)

SSE_POLL_INTERVAL_SECONDS = 0.75
SSE_HEARTBEAT_SECONDS = 15.0
SSE_TERMINAL_IDLE_SECONDS = 30.0


def _encode_sse_event(event: TaskStreamEvent) -> str:
    """Mã hóa event theo wire format SSE."""

    return (
        f"id: {event.event_id}\n"
        "event: task_activity\n"
        f"data: {event.model_dump_json()}\n\n"
    )


async def _stream_task_events(
    request: Request,
    service: ExecutionService,
    source_message_id: str,
    after_sequence: int,
    user_id: str,
) -> AsyncIterator[str]:
    """Replay activity đã lưu, chờ event mới và đóng sau final response."""

    cursor = max(0, after_sequence)
    task_id: str | None = None
    connected_at = monotonic()
    last_sent_at = connected_at
    terminal_since: float | None = None
    sent_count = 0
    disconnect_reason = "CLIENT_DISCONNECTED"
    logger.info(
        "SSE_CONNECTED | source_message_id=%s user_id=%s after_sequence=%s",
        source_message_id,
        user_id,
        cursor,
    )
    try:
        yield "retry: 2000\n\n"
        while not await request.is_disconnected():
            if task_id is None:
                task = await asyncio.to_thread(
                    service.get_task_by_source_message_id,
                    source_message_id,
                )
                if task is not None:
                    task_id = task.id
                    logger.info(
                        "SSE_TASK_BOUND | source_message_id=%s task_id=%s user_id=%s",
                        source_message_id,
                        task_id,
                        user_id,
                    )

            events: list[TaskStreamEvent] = []
            if task_id is not None:
                events = await asyncio.to_thread(
                    service.list_task_stream_events,
                    task_id,
                    cursor,
                    100,
                )
            for event in events:
                yield _encode_sse_event(event)
                cursor = event.sequence_number
                sent_count += 1
                last_sent_at = monotonic()
                if event.event_type.value == "FINAL_RESPONSE_CREATED":
                    disconnect_reason = "FINAL_RESPONSE_CREATED"
                    return
                if event.event_type.value == "TASK_FAILED":
                    activity_data = event.data.get("event_data", {})
                    failure_stage = (
                        activity_data.get("stage")
                        if isinstance(activity_data, dict)
                        else None
                    )
                    if failure_stage in {
                        "PLANNING",
                        "CONFIGURATION",
                        "PLAN_PERSISTENCE",
                    }:
                        disconnect_reason = f"TASK_FAILED_{failure_stage}"
                        return
                    terminal_since = terminal_since or monotonic()

            now = monotonic()
            if (
                terminal_since is not None
                and now - terminal_since >= SSE_TERMINAL_IDLE_SECONDS
            ):
                disconnect_reason = "TERMINAL_IDLE_TIMEOUT"
                return
            if now - last_sent_at >= SSE_HEARTBEAT_SECONDS:
                yield f": heartbeat {int(now)}\n\n"
                last_sent_at = now
            await asyncio.sleep(SSE_POLL_INTERVAL_SECONDS)
    finally:
        logger.info(
            "SSE_DISCONNECTED | source_message_id=%s task_id=%s user_id=%s "
            "last_sequence=%s event_count=%s duration_ms=%s reason=%s",
            source_message_id,
            task_id,
            user_id,
            cursor,
            sent_count,
            int((monotonic() - connected_at) * 1000),
            disconnect_reason,
        )


@device_action_logs_router.get("/", response_model=list[DeviceActionLog])
def list_device_action_logs(
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Audit Log", "View"))],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> list[DeviceActionLog]:
    """Trả nhật ký command bất biến, mới nhất trước."""

    return service.list_device_action_logs(limit)


@device_action_logs_router.get(
    "/by-task/{task_id}",
    response_model=list[DeviceActionLog],
)
def list_device_action_logs_by_task(
    task_id: str,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Audit Log", "View"))],
) -> list[DeviceActionLog]:
    """Chỉ trả command logs của Task cho người có quyền Audit Log View."""

    return service.list_device_action_logs_by_task(task_id)


async def _resume_approved_workflow(
    operation_device_id: str,
    workflow: NetworkAutomationWorkflow,
    benchmark_service: BenchmarkRunService,
) -> None:
    """Resume and finalize a benchmark only after the final Agent response."""

    state = await workflow.resume_after_approval(operation_device_id)
    task = state.get("task")
    if task is not None:
        benchmark_service.complete_for_task(task, state.get("response"))


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "Add"))],
) -> Task:
    return service.create_task(payload)


@router.get("/", response_model=list[Task])
def list_tasks(
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> list[Task]:
    return service.list_tasks()


@router.get("/page", response_model=PageResponse[Task])
def get_task_page(
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 5,
) -> PageResponse[Task]:
    """Trả Task và metadata phân trang trong một response."""

    return service.get_task_page(page=page, page_size=page_size)


@router.get("/by-source-message/{message_id}/events/stream")
async def stream_task_events_by_source_message(
    message_id: str,
    request: Request,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    user: Annotated[User, Depends(require_permission("Task Management", "View"))],
    last_event_id: Annotated[str | None, Header(alias="Last-Event-ID")] = None,
    after_sequence: Annotated[int, Query(ge=0)] = 0,
) -> StreamingResponse:
    """Stream timeline theo source message, hỗ trợ replay sau reconnect."""

    cursor = after_sequence
    if last_event_id is not None:
        try:
            cursor = max(cursor, int(last_event_id))
        except ValueError:
            cursor = after_sequence
    return StreamingResponse(
        _stream_task_events(request, service, message_id, cursor, user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{task_id}", response_model=TaskDetail)
def get_task(
    task_id: str,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> TaskDetail:
    return service.get_task(task_id)


@router.get("/{task_id}/records", response_model=TaskRecords)
def get_task_records(
    task_id: str,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> TaskRecords:
    """Đọc GROUP 3: plan, operation devices, dependency, Agent executions, timeline, approvals."""

    return service.get_task_records(task_id)


@router.get("/{task_id}/activity-events", response_model=list[TaskActivityEvent])
def list_task_activity_events(
    task_id: str,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> list[TaskActivityEvent]:
    """Lấy các bước xử lý của Agent để hiển thị timeline trong Chat UI."""

    return service.list_task_activity_events(task_id)


@router.post(
    "/{task_id}/operations",
    response_model=Operation,
    status_code=status.HTTP_201_CREATED,
)
def create_operation(
    task_id: str,
    payload: OperationCreate,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "Add"))],
) -> Operation:
    return service.create_operation(task_id, payload)


@operations_router.get(
    "/{operation_id}/approvals",
    response_model=list[OperationDeviceApprovalResponse],
)
def list_operation_approvals(
    operation_id: str,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> list[OperationDeviceApprovalResponse]:
    """Lấy yêu cầu phê duyệt của các Device thuộc Operation."""

    return service.list_operation_approvals(operation_id)


@approvals_router.post(
    "/{approval_id}/decision",
    response_model=OperationDeviceApprovalResponse,
)
async def decide_operation_device_approval(
    approval_id: str,
    payload: OperationDeviceApprovalDecision,
    background_tasks: BackgroundTasks,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    workflow: Annotated[
        NetworkAutomationWorkflow,
        Depends(get_network_automation_workflow),
    ],
    benchmark_service: Annotated[
        BenchmarkRunService,
        Depends(get_benchmark_run_service),
    ],
    user: Annotated[User, Depends(require_permission("Task Management", "Approve"))],
) -> OperationDeviceApprovalResponse:
    """Phê duyệt hoặc từ chối một lần bằng User trong access token."""

    approval = await run_in_threadpool(
        service.decide_operation_approval,
        approval_id,
        user_id=user.id,
        decision=payload.decision,
    )
    mapping = await run_in_threadpool(
        service.get_operation_device,
        approval.operation_device_id,
    )
    operation = await run_in_threadpool(service.get_operation, mapping.operation_id)
    await run_in_threadpool(
        service.record_activity,
        operation.task_id,
        ActivityActorType.ORCHESTRATOR,
        (
            ActivityEventType.APPROVAL_APPROVED
            if payload.decision.value == "APPROVED"
            else ActivityEventType.APPROVAL_REJECTED
        ),
        operation_id=operation.id,
        event_data={"approval_id": approval.id, "decided_by": user.id},
    )
    background_tasks.add_task(
        _resume_approved_workflow,
        approval.operation_device_id,
        workflow,
        benchmark_service,
    )
    return approval
