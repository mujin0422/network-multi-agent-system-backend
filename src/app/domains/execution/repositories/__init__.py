"""Persistence ports and adapters for the Execution domain."""

from app.domains.execution.repositories.device_action_log import (
    DeviceActionLogRepository,
)
from app.domains.execution.repositories.unit_of_work import (
    ExecutionRepository,
    ExecutionRepositoryProtocol,
)
from app.domains.execution.repositories.operation import (
    OperationRepository,
    OperationRepositoryProtocol,
)
from app.domains.execution.repositories.operation_dependency import (
    OperationDependencyRepository,
)
from app.domains.execution.repositories.operation_device import (
    OperationDeviceRepository,
    OperationDeviceRepositoryProtocol,
)
from app.domains.execution.repositories.task import (
    TaskRepository,
    TaskRepositoryProtocol,
)
from app.domains.execution.repositories.task_execution import TaskExecutionRepository

__all__ = [
    "DeviceActionLogRepository",
    "ExecutionRepository",
    "ExecutionRepositoryProtocol",
    "OperationDependencyRepository",
    "OperationDeviceRepository",
    "OperationDeviceRepositoryProtocol",
    "OperationRepository",
    "OperationRepositoryProtocol",
    "TaskRepository",
    "TaskRepositoryProtocol",
    "TaskExecutionRepository",
]
