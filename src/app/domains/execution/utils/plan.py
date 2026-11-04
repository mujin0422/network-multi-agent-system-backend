"""Các hàm xây dựng record cho execution plan."""

from dataclasses import dataclass
from datetime import datetime

from app.core.utils import IdPrefix, generate_id
from app.domains.execution.schemas import (
    ExecutionPlanCreate,
    Operation,
    OperationDependency,
    OperationDeviceStatus,
    OperationStatus,
    Task,
    TaskOperationDevice,
    TaskStatus,
)


@dataclass(frozen=True, slots=True)
class ExecutionPlanRecords:
    """Nhóm record đã được dựng để repository lưu trong một transaction."""

    task: Task
    operations: list[Operation]
    dependencies: list[OperationDependency]
    operation_devices: list[TaskOperationDevice]


def build_execution_plan_records(
    task: Task,
    plan: ExecutionPlanCreate,
    created_at: datetime,
    *,
    display_order_start: int = 1,
) -> ExecutionPlanRecords:
    """Chuyển structured plan thành các record có ID và quan hệ đầy đủ."""

    operations: list[Operation] = []
    dependencies: list[OperationDependency] = []
    operation_devices: list[TaskOperationDevice] = []

    for local_order, planned_operation in enumerate(plan.operations, start=1):
        display_order = display_order_start + local_order - 1
        operation = Operation(
            id=generate_id(IdPrefix.OPERATION),
            task_id=task.id,
            operation_intent=planned_operation.operation_intent,
            display_order=display_order,
            operation_status=OperationStatus.PENDING,
            operation_parameters=planned_operation.operation_parameters,
            created_at=created_at,
        )
        operations.append(operation)

        for planned_dependency in planned_operation.dependencies:
            dependencies.append(
                OperationDependency(
                    id=generate_id(IdPrefix.OPERATION_DEPENDENCY),
                    operation_id=operation.id,
                    depends_on_operation_id=operations[
                        planned_dependency.depends_on_order - 1
                    ].id,
                    dependency_type=planned_dependency.dependency_type,
                    created_at=created_at,
                )
            )

        for planned_device in planned_operation.devices:
            operation_devices.append(
                TaskOperationDevice(
                    id=generate_id(IdPrefix.OPERATION_DEVICE),
                    operation_id=operation.id,
                    device_id=planned_device.device_id,
                    operation_device_status=OperationDeviceStatus.PENDING,
                    device_role=planned_device.device_role,
                    access_mode=planned_device.access_mode,
                )
            )

    planned_task = task.model_copy(
        update={
            "task_status": TaskStatus.PLANNING,
            "task_type": plan.task_type,
            "started_at": task.started_at or created_at,
        }
    )
    return ExecutionPlanRecords(
        task=planned_task,
        operations=operations,
        dependencies=dependencies,
        operation_devices=operation_devices,
    )
