"""Quy tắc tổng hợp trạng thái cho Task, Operation và dependency DAG."""

from collections.abc import Iterable, Mapping, Sequence

from app.domains.execution.schemas import (
    DependencyType,
    OperationDependency,
    OperationDeviceStatus,
    OperationStatus,
    TaskOperationDevice,
    TaskStatus,
)


TERMINAL_OPERATION_STATUSES = {
    OperationStatus.SUCCESS,
    OperationStatus.PARTIAL_SUCCESS,
    OperationStatus.FAILED,
    OperationStatus.REJECTED,
    OperationStatus.SKIPPED,
}


def dependencies_satisfied(
    dependencies: Sequence[OperationDependency],
    statuses: Mapping[str, OperationStatus],
) -> bool:
    """Kiểm tra các dependency của Operation đã thỏa điều kiện thực thi."""

    for dependency in dependencies:
        status = statuses.get(dependency.depends_on_operation_id)
        if dependency.dependency_type == DependencyType.ON_SUCCESS:
            if status != OperationStatus.SUCCESS:
                return False
        elif status not in TERMINAL_OPERATION_STATUSES:
            return False
    return True


def task_status(statuses: Iterable[OperationStatus]) -> TaskStatus:
    """Tổng hợp trạng thái Task từ trạng thái cuối của các Operation."""

    values = list(statuses)
    if values and all(value == OperationStatus.SUCCESS for value in values):
        return TaskStatus.SUCCESS
    if any(
        value in {OperationStatus.SUCCESS, OperationStatus.PARTIAL_SUCCESS}
        for value in values
    ):
        return TaskStatus.PARTIAL_SUCCESS
    if values and all(value == OperationStatus.REJECTED for value in values):
        return TaskStatus.REJECTED
    return TaskStatus.FAILED


def operation_status(mappings: Sequence[TaskOperationDevice]) -> OperationStatus:
    """Tổng hợp trạng thái Operation từ các operation-device mapping."""

    statuses = [mapping.operation_device_status for mapping in mappings]
    if OperationDeviceStatus.WAITING_APPROVAL in statuses:
        return OperationStatus.WAITING_APPROVAL
    if statuses and all(status == OperationDeviceStatus.SUCCESS for status in statuses):
        return OperationStatus.SUCCESS
    if statuses and all(status == OperationDeviceStatus.REJECTED for status in statuses):
        return OperationStatus.REJECTED
    if OperationDeviceStatus.SUCCESS in statuses:
        return OperationStatus.PARTIAL_SUCCESS
    return OperationStatus.FAILED
