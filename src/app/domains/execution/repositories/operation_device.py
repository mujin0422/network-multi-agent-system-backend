"""Persistence contract và repository cho bảng task_operation_devices."""

from typing import Any, Protocol

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import TaskOperationDeviceModel
from app.domains.execution.schemas import TaskOperationDevice


class OperationDeviceRepositoryProtocol(Protocol):
    """Contract đọc mapping trong bảng task_operation_devices."""

    def get_all_by_operation_id(
        self,
        operation_id: str,
    ) -> list[TaskOperationDevice]:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_all_by_operation_id."""
        ...
    def get_by_id(
        self,
        operation_device_id: str,
    ) -> TaskOperationDevice | None:
        """Truy vấn dữ liệu theo phạm vi của phương thức get_by_id."""
        ...
    def save_operation_device(self, mapping: TaskOperationDevice) -> None:
        """Lưu dữ liệu theo nghiệp vụ của phương thức save_operation_device."""
        ...


class OperationDeviceRepository:
    """Quản lý thiết bị, role và access mode được gán cho operation."""

    def __init__(self, database_url: str) -> None:
        """Khởi tạo OperationDeviceRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)

    def get_all_by_operation_id(
        self,
        operation_id: str,
    ) -> list[TaskOperationDevice]:
        """Lấy tất cả device mapping mà Network Agent phải thực thi."""

        statement = select(TaskOperationDeviceModel).where(
            TaskOperationDeviceModel.operation_id == operation_id
        )
        with self._sessions() as session:
            return [
                TaskOperationDevice.model_validate(model, from_attributes=True)
                for model in session.scalars(statement).all()
            ]

    def save_operation_device(self, mapping: TaskOperationDevice) -> None:
        """Tạo hoặc cập nhật trạng thái thực thi trên một thiết bị."""

        with self._sessions.begin() as session:
            model = session.get(TaskOperationDeviceModel, mapping.id)
            if model is None:
                session.add(TaskOperationDeviceModel(**mapping.model_dump()))
                return
            model.operation_device_status = mapping.operation_device_status
            model.error_message = mapping.error_message
            model.started_at = mapping.started_at
            model.completed_at = mapping.completed_at

    def get_by_id(
        self,
        operation_device_id: str,
    ) -> TaskOperationDevice | None:
        """Lấy một mapping để tiếp tục Task sau quyết định Approval."""

        with self._sessions() as session:
            model = session.get(TaskOperationDeviceModel, operation_device_id)
            return (
                TaskOperationDevice.model_validate(model, from_attributes=True)
                if model
                else None
            )

    @staticmethod
    def add_all_in_session(
        session: Any,
        mappings: list[TaskOperationDevice],
    ) -> None:
        """Thêm mappings bằng session chung, không tự commit transaction."""

        session.add_all(
            TaskOperationDeviceModel(**item.model_dump()) for item in mappings
        )
