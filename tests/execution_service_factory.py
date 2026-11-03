"""Test-only composition helper cho các stub Execution cũ."""

from types import SimpleNamespace

from app.domains.execution.services import ExecutionService


def build_execution_service_stub(repository: object) -> ExecutionService:
    """Tách một stub tổng hợp thành dependency theo từng repository contract."""

    def method(name: str, fallback=None):
        value = getattr(repository, name, None)
        if value is not None:
            return value
        if fallback is not None:
            return fallback

        def missing(*_args, **_kwargs):
            raise NotImplementedError(name)

        return missing

    tasks = SimpleNamespace(
        get_by_source_message_id=method("get_task_by_source_message_id"),
        save_task=method("save_task"),
        get_all=method("get_all_tasks", lambda: []),
        get_by_id=method("get_task_by_id"),
    )
    operations = SimpleNamespace(
        save_operation=method("save_operation"),
        get_by_id=method("get_operation_by_id"),
        get_all_by_task_id=method("get_all_operations_by_task_id", lambda _id: []),
    )
    operation_devices = SimpleNamespace(
        get_all_by_operation_id=method(
            "get_all_operation_devices_by_operation_id", lambda _id: []
        ),
        get_by_id=method("get_operation_device_by_id"),
        save_operation_device=method(
            "save_operation_device",
            lambda item: repository.operation_devices.append(item),
        ),
    )
    dependencies = SimpleNamespace(
        get_all_by_operation_id=method(
            "get_all_dependencies_by_operation_id", lambda _id: []
        ),
        save=method(
            "save_operation_dependencies",
            lambda items: repository.dependencies.extend(items),
        ),
    )
    task_executions = SimpleNamespace(
        get_all_by_task_id=method(
            "get_all_task_executions_by_task_id", lambda _id: []
        ),
        save=method("save_task_execution"),
    )
    action_logs = SimpleNamespace(
        get_recent=method("get_recent_device_action_logs", lambda _limit=500: []),
        get_all_by_task_id=method(
            "get_all_device_action_logs_by_task_id", lambda _id: []
        ),
        save_all=method("save_device_action_logs"),
    )
    activities = SimpleNamespace(
        get_all_by_task_id=method(
            "get_all_task_activity_events_by_task_id", lambda _id: []
        ),
        save_task_activity_event=method("save_task_activity_event"),
    )
    approvals = SimpleNamespace(
        get_all_by_operation_id=method(
            "get_all_operation_approvals_by_operation_id", lambda _id: []
        ),
        get_by_operation_device_id=method("get_approval_by_operation_device_id"),
        save_operation_device_approval=method("save_operation_device_approval"),
        get_by_id=method("get_operation_approval_by_id"),
        expire_operation_approval=method("expire_operation_approval"),
        decide_operation_approval=method("decide_operation_approval"),
    )
    approval_timeouts = SimpleNamespace(
        expire_due_approvals=method("expire_due_approvals", lambda _now, _ttl: [])
    )
    return ExecutionService(
        tasks,
        operations,
        operation_devices,
        dependencies,
        task_executions,
        action_logs,
        activities,
        approvals,
        approval_timeouts,
    )
