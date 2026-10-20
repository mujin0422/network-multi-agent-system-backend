"""Contracts dùng để tạo execution plan từ Planner Agent."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.execution.schemas.operation_dependency import DependencyType
from app.domains.execution.schemas.operation_device import AccessMode, DeviceRole
from app.domains.execution.schemas.task import TaskType


class PlannedDevice(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    device_id: str = Field(min_length=1)
    device_role: DeviceRole
    access_mode: AccessMode

    @model_validator(mode="after")
    def validate_role_access(self) -> "PlannedDevice":
        if self.device_role in {DeviceRole.SOURCE, DeviceRole.CONTEXT}:
            if self.access_mode != AccessMode.READ:
                raise ValueError("SOURCE và CONTEXT chỉ được sử dụng READ access")
        return self


class PlannedDependency(BaseModel):
    depends_on_order: int = Field(ge=1)
    dependency_type: DependencyType = DependencyType.ON_SUCCESS


class PlannedOperation(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    operation_intent: str = Field(min_length=1, max_length=100)
    operation_parameters: dict[str, Any] = Field(default_factory=dict)
    devices: list[PlannedDevice] = Field(default_factory=list)
    dependencies: list[PlannedDependency] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_device_commands(self) -> "PlannedOperation":
        """Operation gắn thiết bị phải có ít nhất một command hợp lệ."""

        if not self.devices:
            return self
        raw_commands = self.operation_parameters.get(
            "commands", self.operation_parameters.get("command")
        )
        if isinstance(raw_commands, str) and raw_commands.strip():
            return self
        if isinstance(raw_commands, list) and any(
            isinstance(command, str) and command.strip() for command in raw_commands
        ):
            return self
        raise ValueError("Operation có device phải cung cấp command hợp lệ")


class ExecutionPlanCreate(BaseModel):
    task_type: TaskType
    operations: list[PlannedOperation] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dependency_graph(self) -> "ExecutionPlanCreate":
        for order, operation in enumerate(self.operations, start=1):
            dependency_orders = [
                item.depends_on_order for item in operation.dependencies
            ]
            if len(dependency_orders) != len(set(dependency_orders)):
                raise ValueError(f"Operation {order} có dependency trùng lặp")
            if any(dependency_order >= order for dependency_order in dependency_orders):
                raise ValueError("Dependency phải tham chiếu operation đứng trước")

            device_ids = [item.device_id for item in operation.devices]
            if len(device_ids) != len(set(device_ids)):
                raise ValueError(f"Operation {order} có device trùng lặp")
        return self
