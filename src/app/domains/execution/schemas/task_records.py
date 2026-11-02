"""Read-only GROUP 3 execution records associated with a Task."""

from pydantic import BaseModel

from app.domains.execution.schemas.operation_dependency import OperationDependency
from app.domains.execution.schemas.operation_device import TaskOperationDevice
from app.domains.execution.schemas.operation_device_approval import (
    OperationDeviceApprovalResponse,
)
from app.domains.execution.schemas.task import TaskDetail
from app.domains.execution.schemas.task_activity_event import TaskActivityEvent
from app.domains.execution.schemas.task_execution import TaskExecution


class TaskRecords(BaseModel):
    """Records for Task Management View; command logs require Audit Log View separately."""

    task: TaskDetail
    operation_devices: list[TaskOperationDevice]
    dependencies: list[OperationDependency]
    executions: list[TaskExecution]
    activity_events: list[TaskActivityEvent]
    approvals: list[OperationDeviceApprovalResponse]
