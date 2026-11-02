"""Canonical hashing for immutable operation-device approval snapshots."""

import hashlib
import json
from datetime import datetime

from app.core.utils import IdPrefix, generate_id
from app.domains.execution.schemas import (
    ApprovalStatus,
    Operation,
    OperationDeviceApproval,
    OperationDeviceApprovalResponse,
    RiskLevel,
    TaskOperationDevice,
)


def build_approval_request_hash(
    operation_device_id: str,
    commands: list[str],
) -> str:
    """Hash mapping ID and ordered commands using canonical UTF-8 JSON."""

    canonical_payload = json.dumps(
        {
            "commands": commands,
            "operation_device_id": operation_device_id,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical_payload.encode()).hexdigest()


def build_operation_device_approval(
    operation: Operation,
    mapping: TaskOperationDevice,
    commands: list[str],
    request_hash: str,
    requested_at: datetime,
) -> OperationDeviceApproval:
    """Tạo snapshot phê duyệt bất biến trước khi thực thi lệnh WRITE."""

    return OperationDeviceApproval(
        id=generate_id(IdPrefix.OPERATION_DEVICE_APPROVAL),
        operation_device_id=mapping.id,
        approval_status=ApprovalStatus.PENDING,
        risk_level=RiskLevel.HIGH,
        requested_by="execution-orchestrator",
        reason=(
            f"Operation {operation.operation_intent} sẽ thay đổi cấu hình "
            f"trên thiết bị {mapping.device_id}."
        ),
        commands_snapshot=commands,
        request_hash=request_hash,
        requested_at=requested_at,
        created_at=requested_at,
    )


def to_approval_response(
    approval: OperationDeviceApproval,
) -> OperationDeviceApprovalResponse:
    """Ẩn request hash trước khi trả dữ liệu phê duyệt cho API."""

    return OperationDeviceApprovalResponse.model_validate(
        approval.model_dump(exclude={"request_hash"})
    )
