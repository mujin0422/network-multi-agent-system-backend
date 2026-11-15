"""Contracts dùng để tạo execution plan từ Planner Agent."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.execution.schemas.operation_dependency import DependencyType
from app.domains.execution.schemas.operation_device import AccessMode, DeviceRole
from app.domains.execution.schemas.task import TaskType


class PlannedDevice(BaseModel):
    """Thiết bị mạng được Planner Agent dự kiến sử dụng trong một operation."""
    model_config = ConfigDict(str_strip_whitespace=True)

    device_id: str = Field(min_length=1, description="ID của thiết bị mạng.")
    device_role: DeviceRole = Field(description="Vai trò của thiết bị trong operation.")
    access_mode: AccessMode = Field(description="Quyền truy cập thiết bị trong operation.")

    @model_validator(mode="after")
    def validate_role_access(self) -> "PlannedDevice":
        if self.device_role in {DeviceRole.SOURCE, DeviceRole.CONTEXT}:
            if self.access_mode != AccessMode.READ:
                raise ValueError("SOURCE và CONTEXT chỉ được sử dụng READ access")
        return self


class PlannedDependency(BaseModel):
    """Dependency giữa hai operation trong cùng Task."""

    depends_on_order: int = Field(ge=1, description="Thứ tự operation tiên quyết trong cùng Task.")
    dependency_type: DependencyType = Field(description="Loại dependency giữa hai operation trong cùng Task.", default=DependencyType.ON_SUCCESS)


class PlannedOperation(BaseModel):
    """Operation dự kiến được Planner Agent tạo ra trong execution plan."""
    model_config = ConfigDict(str_strip_whitespace=True)

    operation_intent: str = Field(min_length=1, max_length=100, description="Mục đích của operation.")
    operation_parameters: dict[str, Any] = Field(default_factory=dict, description="Tham số JSON object của operation.")
    devices: list[PlannedDevice] = Field(default_factory=list, description="Danh sách thiết bị mạng được sử dụng trong operation.")
    dependencies: list[PlannedDependency] = Field(default_factory=list, description="Danh sách dependency của operation.")

    @model_validator(mode="after")
    def validate_device_commands(self) -> "PlannedOperation":
        """READ cần command; WRITE có thể chờ Configuration Agent biên dịch."""

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
        has_write_device = any(
            device.access_mode == AccessMode.WRITE for device in self.devices
        )
        requirements = self.operation_parameters.get("configuration_requirements")
        if has_write_device and isinstance(requirements, dict) and requirements:
            return self
        raise ValueError("Operation có device phải cung cấp command hợp lệ")


class ExecutionPlanCreate(BaseModel):
    """Payload tạo execution plan từ Planner Agent."""
    task_type: TaskType = Field(default=TaskType.UNCLASSIFIED, description="Loại mục tiêu của Task.")
    operations: list[PlannedOperation] = Field(min_length=1, description="Danh sách operation được sắp theo display_order.")

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
