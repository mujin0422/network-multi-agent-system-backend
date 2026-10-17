"""HTTP routes của AI Execution Management domain."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.domains.execution.schemas import (
    Operation,
    OperationCreate,
    Task,
    TaskCreate,
    TaskDetail,
)
from app.domains.execution.services import ExecutionService
from app.domains.execution.routers.dependencies import get_execution_service


router = APIRouter()
operations_router = APIRouter()


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
