"""Composition factory cho ExecutionService."""

from app.domains.execution.repositories import (
    ApprovalTimeoutRepository,
    DeviceActionLogRepository,
    OperationDependencyRepository,
    OperationDeviceApprovalRepository,
    OperationDeviceRepository,
    OperationRepository,
    TaskActivityEventRepository,
    TaskExecutionRepository,
    TaskRepository,
)
from app.domains.execution.services.execution import ExecutionService


def build_execution_service(database_url: str) -> ExecutionService:
    """Khởi tạo service với repository chuyên trách cho từng bảng."""

    return ExecutionService(
        TaskRepository(database_url),
        OperationRepository(database_url),
        OperationDeviceRepository(database_url),
        OperationDependencyRepository(database_url),
        TaskExecutionRepository(database_url),
        DeviceActionLogRepository(database_url),
        TaskActivityEventRepository(database_url),
        OperationDeviceApprovalRepository(database_url),
        ApprovalTimeoutRepository(database_url),
    )
