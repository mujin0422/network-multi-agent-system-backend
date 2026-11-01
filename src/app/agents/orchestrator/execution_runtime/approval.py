"""Approval gate bảo vệ mọi operation WRITE trước khi thực thi."""

from datetime import UTC, datetime

from app.domains.execution.schemas import (
    AccessMode,
    ApprovalStatus,
    Operation,
    OperationDeviceStatus,
    TaskOperationDevice,
)
from app.domains.execution.services import ExecutionService
from app.domains.execution.utils import build_approval_request_hash


class ApprovalGate:
    """Xác nhận mapping READ/WRITE có đủ điều kiện đi tới Network Agent."""

    def __init__(self, execution_service: ExecutionService) -> None:
        """Khởi tạo gate với service quản lý approval và device mapping."""

        self._execution_service = execution_service

    def can_execute(
        self,
        operation: Operation,
        mapping: TaskOperationDevice,
        commands: list[str],
    ) -> bool:
        """Kiểm tra READ/WRITE mapping có đủ điều kiện được thực thi hay không."""

        if mapping.operation_device_status in {
            OperationDeviceStatus.SUCCESS,
            OperationDeviceStatus.REJECTED,
            OperationDeviceStatus.SKIPPED,
        }:
            return False
        if mapping.access_mode == AccessMode.READ:
            return True

        approval = self._execution_service.get_operation_device_approval(mapping.id)
        if approval is None:
            self._execution_service.create_operation_device_approval(
                operation,
                mapping,
                commands,
                build_approval_request_hash(mapping.id, commands),
            )
            self._wait(mapping)
            return False

        now = datetime.now(UTC)
        if approval.approval_status == ApprovalStatus.PENDING:
            if approval.expires_at is not None and approval.expires_at <= now:
                self._execution_service.expire_operation_approval(approval.id)
                self._reject(mapping, "Yêu cầu phê duyệt đã hết hạn")
            else:
                self._wait(mapping)
            return False
        if approval.approval_status in {
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXPIRED,
        }:
            self._reject(mapping, "Cấu hình không được phê duyệt")
            return False

        expected_hash = build_approval_request_hash(mapping.id, commands)
        if approval.commands_snapshot != commands or approval.request_hash != expected_hash:
            self._fail(
                mapping,
                "Command hiện tại không khớp snapshot đã được phê duyệt",
            )
            return False
        return True

    def _wait(self, mapping: TaskOperationDevice) -> None:
        """Đưa mapping về trạng thái chờ quyết định phê duyệt."""

        self._update_mapping(
            mapping,
            OperationDeviceStatus.WAITING_APPROVAL,
            error_message=None,
            completed_at=None,
        )

    def _reject(self, mapping: TaskOperationDevice, error_message: str) -> None:
        """Đánh dấu mapping bị từ chối và lưu lý do nghiệp vụ."""

        self._update_mapping(
            mapping,
            OperationDeviceStatus.REJECTED,
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

    def _fail(self, mapping: TaskOperationDevice, error_message: str) -> None:
        """Đánh dấu mapping thất bại khi dữ liệu approval không còn toàn vẹn."""

        self._update_mapping(
            mapping,
            OperationDeviceStatus.FAILED,
            error_message=error_message,
            completed_at=datetime.now(UTC),
        )

    def _update_mapping(
        self,
        mapping: TaskOperationDevice,
        status: OperationDeviceStatus,
        *,
        error_message: str | None,
        completed_at: datetime | None,
    ) -> None:
        """Lưu trạng thái approval mới vào operation-device mapping."""

        self._execution_service.update_operation_device(
            mapping.model_copy(
                update={
                    "operation_device_status": status,
                    "error_message": error_message,
                    "completed_at": completed_at,
                }
            )
        )
