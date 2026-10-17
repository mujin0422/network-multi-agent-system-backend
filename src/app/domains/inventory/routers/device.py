"""HTTP routes cung cấp Network Inventory cho frontend."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.domains.inventory.schemas import Device, DeviceCreate, DeviceUpdate
from app.domains.inventory.routers.dependencies import get_device_service
from app.domains.inventory.services import DeviceService


router = APIRouter()


# CREATE — Thêm một thiết bị mới vào inventory.
@router.post(
    "/",
    response_model=Device,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm thiết bị",
)
async def create_device(
    payload: DeviceCreate,
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> Device:
    """Tạo device mới sau khi kiểm tra hostname và host/port không bị trùng."""

    return service.create_device(payload)


# READ — Lấy danh sách toàn bộ thiết bị.
@router.get("/", response_model=list[Device], summary="Lấy danh sách thiết bị")
async def list_devices(
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> list[Device]:
    """Trả danh sách device hiện có trong inventory."""

    return service.list_devices()


# READ — Lấy chi tiết một thiết bị theo hostname.
# Route tĩnh này phải đặt trước /{device_id} để không bị nhận nhầm thành ID.
@router.get(
    "/by-hostname/{hostname}",
    response_model=Device,
    summary="Lấy thiết bị theo hostname",
)
async def get_device_by_hostname(
    hostname: str,
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> Device:
    """Tìm Device theo hostname, không phân biệt chữ hoa và chữ thường."""

    return service.get_device_by_hostname(hostname)


# READ — Lấy chi tiết một thiết bị theo ID.
@router.get(
    "/{device_id}",
    response_model=Device,
    summary="Lấy chi tiết thiết bị",
)
async def get_device(
    device_id: str,
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> Device:
    """Trả device tương ứng hoặc HTTP 404 nếu ID không tồn tại."""

    return service.get_device(device_id)


# UPDATE — Sửa một phần thông tin thiết bị theo ID.
@router.patch(
    "/{device_id}",
    response_model=Device,
    summary="Cập nhật thiết bị",
)
async def update_device(
    device_id: str,
    payload: DeviceUpdate,
    service: Annotated[DeviceService, Depends(get_device_service)],
) -> Device:
    """Chỉ cập nhật các trường được gửi lên và giữ nguyên trường còn lại."""

    return service.update_device(device_id, payload)


# DELETE chưa được triển khai vì cần xác định chính sách xóa device đang được
# tham chiếu bởi task_operation_devices và device_action_logs.
