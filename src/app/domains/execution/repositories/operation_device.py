"""Repository cho bảng task_operation_devices."""

from sqlalchemy import select

from app.core.database import create_session_factory
from app.domains.execution.models import TaskOperationDeviceModel
from app.domains.execution.schemas import OperationDeviceStatus, TaskOperationDevice


class OperationDeviceRepository:

    def __init__(self, database_url: str) -> None:
        """Khởi tạo OperationDeviceRepository cùng các phụ thuộc cần thiết."""
        self._sessions = create_session_factory(database_url)


    def get_all_by_operation_id(self, operation_id: str) -> list[TaskOperationDevice]:
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
            model = session.get(TaskOperationDeviceModel, mapping.id, with_for_update=True)
            if model is None:
                session.add(TaskOperationDeviceModel(**mapping.model_dump()))
                return
            if model.operation_device_status in {
                OperationDeviceStatus.SUCCESS, OperationDeviceStatus.FAILED,
                OperationDeviceStatus.REJECTED, OperationDeviceStatus.SKIPPED,
            }:
                return
            model.operation_device_status = mapping.operation_device_status
            model.error_message = mapping.error_message
            model.started_at = mapping.started_at
            model.completed_at = mapping.completed_at


    def get_by_id(self, operation_device_id: str,) -> TaskOperationDevice | None:
        """Lấy một mapping để tiếp tục Task sau quyết định Approval."""
        with self._sessions() as session:
            model = session.get(TaskOperationDeviceModel, operation_device_id)
            return (
                TaskOperationDevice.model_validate(model, from_attributes=True)
                if model
                else None
            )

