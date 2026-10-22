"""HTTP routes của AI Execution Management domain."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from app.agents.dependencies import get_analysis_orchestrator, get_execution_orchestrator
from app.agents.orchestrator import AnalysisOrchestrator, ExecutionOrchestrator
from app.domains.identity.routers.dependencies import require_permission
from app.domains.identity.schemas import User

from app.domains.execution.schemas import (
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
)
from app.domains.execution.services import ExecutionService
from app.domains.execution.routers.dependencies import get_execution_service


router = APIRouter()
operations_router = APIRouter()
approvals_router = APIRouter()


async def _resume_approved_workflow(
    operation_device_id: str,
    service: ExecutionService,
    execution_orchestrator: ExecutionOrchestrator,
    analysis_orchestrator: AnalysisOrchestrator,
) -> None:
    """Tiếp tục execution và analysis sau khi response phê duyệt đã trả."""

    mapping = service.get_operation_device(operation_device_id)
    operation = service.get_operation(mapping.operation_id)
    task = service.get_task(operation.task_id)
    results = await execution_orchestrator.resume_after_approval(operation_device_id)
    await analysis_orchestrator.analyze_and_respond(task, results)


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "Add"))],
) -> Task:
    return service.create_task(payload)


@router.get("/", response_model=list[Task])
async def list_tasks(
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> list[Task]:
    return service.list_tasks()


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: str,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "View"))],
) -> TaskDetail:
    return service.get_task(task_id)


@router.get("/{task_id}/activity-events", response_model=list[TaskActivityEvent])
async def list_task_activity_events(
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
async def add_operation(
    task_id: str,
    payload: OperationCreate,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
    _user: Annotated[User, Depends(require_permission("Task Management", "Add"))],
) -> Operation:
    return service.add_operation(task_id, payload)


@operations_router.get(
    "/{operation_id}/approvals",
    response_model=list[OperationDeviceApprovalResponse],
)
async def list_operation_approvals(
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
    execution_orchestrator: Annotated[
        ExecutionOrchestrator,
        Depends(get_execution_orchestrator),
    ],
    analysis_orchestrator: Annotated[
        AnalysisOrchestrator,
        Depends(get_analysis_orchestrator),
    ],
    user: Annotated[User, Depends(require_permission("Task Management", "Approve"))],
) -> OperationDeviceApprovalResponse:
    """Phê duyệt hoặc từ chối một lần bằng User trong access token."""

    approval = service.decide_operation_approval(
        approval_id,
        user.id,
        payload.decision,
    )
    mapping = service.get_operation_device(approval.operation_device_id)
    operation = service.get_operation(mapping.operation_id)
    service.record_activity(
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
        service,
        execution_orchestrator,
        analysis_orchestrator,
    )
    return approval
