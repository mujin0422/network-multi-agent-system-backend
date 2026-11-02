"""Các repository công khai của Execution domain."""

from app.domains.execution.repositories.device_action_log import (
    DeviceActionLogRepository,
)
from app.domains.execution.repositories.unit_of_work import ExecutionRepository
from app.domains.execution.repositories.operation import OperationRepository
from app.domains.execution.repositories.operation_dependency import (
    OperationDependencyRepository,
)
from app.domains.execution.repositories.operation_device import OperationDeviceRepository
from app.domains.execution.repositories.operation_device_approval import OperationDeviceApprovalRepository
from app.domains.execution.repositories.task import TaskRepository
from app.domains.execution.repositories.task_activity_event import TaskActivityEventRepository
from app.domains.execution.repositories.task_execution import TaskExecutionRepository

__all__ = [
    "DeviceActionLogRepository",
    "ExecutionRepository",
    "OperationDependencyRepository",
    "OperationDeviceRepository",
    "OperationDeviceApprovalRepository",
    "OperationRepository",
    "TaskRepository",
    "TaskActivityEventRepository",
    "TaskExecutionRepository",
]
