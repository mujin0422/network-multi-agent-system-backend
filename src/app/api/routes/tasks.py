"""HTTP routes của AI Execution Management domain."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_execution_service
from app.domains.execution.schemas import (
    ChangeSet,
    ChangeSetApproval,
    ChangeSetCreate,
    Operation,
    OperationCreate,
    Task,
    TaskCreate,
    TaskDetail,
)
from app.domains.execution.service import ExecutionService


router = APIRouter()
operations_router = APIRouter()
change_sets_router = APIRouter()


@router.post("/", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> Task:
    return service.create_task(payload)


@router.get("/", response_model=list[Task])
async def list_tasks(
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> list[Task]:
    return service.list_tasks()


@router.get("/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: str,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> TaskDetail:
    return service.get_task(task_id)


@router.post(
    "/{task_id}/operations",
    response_model=Operation,
    status_code=status.HTTP_201_CREATED,
)
async def add_operation(
    task_id: str,
    payload: OperationCreate,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> Operation:
    return service.add_operation(task_id, payload)


@operations_router.post(
    "/{operation_id}/change-sets",
    response_model=ChangeSet,
    status_code=status.HTTP_201_CREATED,
)
async def create_change_set(
    operation_id: str,
    payload: ChangeSetCreate,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> ChangeSet:
    return service.create_change_set(operation_id, payload)


@change_sets_router.post(
    "/{change_set_id}/approve",
    response_model=ChangeSet,
)
async def approve_change_set(
    change_set_id: str,
    payload: ChangeSetApproval,
    service: Annotated[ExecutionService, Depends(get_execution_service)],
) -> ChangeSet:
    return service.approve_change_set(change_set_id, payload)
