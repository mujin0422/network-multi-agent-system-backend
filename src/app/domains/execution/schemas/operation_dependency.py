"""Schema ánh xạ bảng ``operation_dependencies``."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DependencyType(StrEnum):
    ON_SUCCESS = "ON_SUCCESS"
    ON_COMPLETION = "ON_COMPLETION"


class OperationDependency(BaseModel):
    """Cạnh có hướng trong DAG execution plan của một Task."""

    id: str = Field(description="Khóa chính của dependency.")
    operation_id: str = Field(description="Operation chỉ được chạy sau dependency.")
    depends_on_operation_id: str = Field(
        description="Operation tiên quyết trong cùng Task.",
    )
    dependency_type: DependencyType = Field(
        description="Điều kiện ON_SUCCESS hoặc ON_COMPLETION.",
    )
    created_at: datetime = Field(description="Thời điểm tạo dependency theo UTC.")
