"""SQLAlchemy models owned by the Execution domain."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.domains.execution.schemas import AccessMode, DependencyType, DeviceActionPhase, DeviceActionStatus, DeviceActionType, DeviceRole, ExecutionStatus, OperationDeviceStatus, OperationStatus, TaskStatus, TaskType


class TaskModel(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    source_message_id: Mapped[str] = mapped_column(ForeignKey("messages.id"), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    input_message: Mapped[str] = mapped_column(Text)
    task_status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"))
    task_type: Mapped[TaskType] = mapped_column(Enum(TaskType, name="task_type"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class OperationModel(Base):
    __tablename__ = "task_operations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    operation_intent: Mapped[str] = mapped_column(String(100))
    display_order: Mapped[int] = mapped_column(Integer)
    operation_status: Mapped[OperationStatus] = mapped_column(Enum(OperationStatus, name="operation_status"))
    operation_parameters: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OperationDependencyModel(Base):
    __tablename__ = "operation_dependencies"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation_id: Mapped[str] = mapped_column(ForeignKey("task_operations.id"))
    depends_on_operation_id: Mapped[str] = mapped_column(ForeignKey("task_operations.id"))
    dependency_type: Mapped[DependencyType] = mapped_column(Enum(DependencyType, name="dependency_type"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TaskOperationDeviceModel(Base):
    __tablename__ = "task_operation_devices"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation_id: Mapped[str] = mapped_column(ForeignKey("task_operations.id"))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    operation_device_status: Mapped[OperationDeviceStatus] = mapped_column(Enum(OperationDeviceStatus, name="operation_device_status"))
    device_role: Mapped[DeviceRole] = mapped_column(Enum(DeviceRole, name="device_role"))
    access_mode: Mapped[AccessMode] = mapped_column(Enum(AccessMode, name="access_mode"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TaskExecutionModel(Base):
    __tablename__ = "task_executions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    operation_id: Mapped[str | None] = mapped_column(ForeignKey("task_operations.id"))
    operation_device_id: Mapped[str | None] = mapped_column(ForeignKey("task_operation_devices.id"))
    agent_name: Mapped[str] = mapped_column(String(100))
    tool_name: Mapped[str | None] = mapped_column(String(100))
    step_order: Mapped[int] = mapped_column(Integer)
    input: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    output: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    execution_status: Mapped[ExecutionStatus] = mapped_column(Enum(ExecutionStatus, name="execution_status"))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DeviceActionLogModel(Base):
    __tablename__ = "device_action_logs"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"))
    operation_id: Mapped[str] = mapped_column(ForeignKey("task_operations.id"))
    operation_device_id: Mapped[str] = mapped_column(ForeignKey("task_operation_devices.id"))
    execution_id: Mapped[str] = mapped_column(ForeignKey("task_executions.id"))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    rollback_of_action_id: Mapped[UUID | None] = mapped_column(ForeignKey("device_action_logs.id"))
    action_type: Mapped[DeviceActionType] = mapped_column(Enum(DeviceActionType, name="device_action_type"))
    action_phase: Mapped[DeviceActionPhase] = mapped_column(Enum(DeviceActionPhase, name="device_action_phase"))
    sequence_number: Mapped[int] = mapped_column(Integer)
    command: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text)
    action_log_status: Mapped[DeviceActionStatus] = mapped_column(Enum(DeviceActionStatus, name="device_action_status"))
    error_message: Mapped[str | None] = mapped_column(Text)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
