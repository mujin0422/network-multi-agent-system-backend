"""Workflow enums shared by Task and Operation contracts."""

from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class TaskType(StrEnum):
    UNCLASSIFIED = "UNCLASSIFIED"
    INFORMATION_RETRIEVAL = "INFORMATION_RETRIEVAL"
    DIAGNOSIS = "DIAGNOSIS"
    CONFIGURATION = "CONFIGURATION"
    REMEDIATION = "REMEDIATION"
    COMPOSITE = "COMPOSITE"


class OperationStatus(StrEnum):
    PENDING = "PENDING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class OperationDeviceStatus(StrEnum):
    PENDING = "PENDING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class DeviceRole(StrEnum):
    SOURCE = "SOURCE"
    TARGET = "TARGET"
    CONTEXT = "CONTEXT"


class AccessMode(StrEnum):
    READ = "READ"
    WRITE = "WRITE"


class DependencyType(StrEnum):
    ON_SUCCESS = "ON_SUCCESS"
    ON_COMPLETION = "ON_COMPLETION"


class ExecutionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DeviceActionStatus(StrEnum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class DeviceActionType(StrEnum):
    READ = "READ"
    WRITE = "WRITE"


class DeviceActionPhase(StrEnum):
    READ = "READ"
    PRE_CHECK = "PRE_CHECK"
    APPLY = "APPLY"
    POST_CHECK = "POST_CHECK"
    ROLLBACK = "ROLLBACK"
    ROLLBACK_VERIFY = "ROLLBACK_VERIFY"
