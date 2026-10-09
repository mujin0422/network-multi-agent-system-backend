"""Contracts và state enum của AI Execution Management domain."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"


class OperationStatus(StrEnum):
    PENDING = "PENDING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    SKIPPED = "SKIPPED"


class ChangeSetStatus(StrEnum):
    PLANNED = "PLANNED"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"


class TaskCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    conversation_id: str = Field(min_length=1)
    source_message_id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    input_message: str = Field(min_length=1)


class Task(BaseModel):
    id: str
    conversation_id: str
    source_message_id: str
    user_id: str
    input_message: str
    status: TaskStatus
    created_at: datetime
    completed_at: datetime | None = None


class OperationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    intent: str = Field(min_length=1, max_length=100)
    display_order: int = Field(ge=1)
    parameters: dict[str, Any] = Field(default_factory=dict)


class Operation(BaseModel):
    id: str
    task_id: str
    intent: str
    display_order: int
    status: OperationStatus
    parameters: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None = None


class ChangeSetCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    device_id: str = Field(min_length=1)
    pre_change_snapshot: str = Field(min_length=1)
    planned_commands: list[str] = Field(min_length=1)
    rollback_commands: list[str] = Field(min_length=1)
    verification_checks: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_blank_commands(self) -> "ChangeSetCreate":
        command_groups = (
            self.planned_commands,
            self.rollback_commands,
            self.verification_checks,
        )
        if any(not command.strip() for group in command_groups for command in group):
            raise ValueError("Command và verification check không được để trống")
        return self


class ChangeSet(BaseModel):
    id: str
    operation_id: str
    device_id: str
    pre_change_snapshot: str
    planned_commands: list[str]
    rollback_commands: list[str]
    verification_checks: list[str]
    status: ChangeSetStatus
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime


class ChangeSetApproval(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    approved_by: str = Field(min_length=1)


class TaskDetail(Task):
    operations: list[Operation] = Field(default_factory=list)
