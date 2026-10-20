"""Các use case và quy tắc nghiệp vụ của resource Device."""

from datetime import UTC, datetime
from math import ceil

from app.core.exceptions import ResourceConflictError, ResourceNotFoundError
from app.core.utils import IdPrefix, generate_id
from app.domains.inventory.repositories import DeviceRepositoryProtocol
from app.domains.inventory.schemas import Device, DeviceCreate, DevicePage, DeviceUpdate


class DeviceService:
    """Điểm vào công khai cho thao tác tạo, đọc và cập nhật thiết bị."""

    def __init__(self, repository: DeviceRepositoryProtocol) -> None:
        self._repository = repository

    def create_device(self, payload: DeviceCreate) -> Device:
        """Kiểm tra uniqueness, sinh ID/timestamp rồi lưu thiết bị mới."""
        self._ensure_unique_device(payload.hostname, payload.host, payload.port)
        # Dùng UTC để timestamp nhất quán giữa local, Docker và production.
        now = datetime.now(UTC)
        device = Device(
            id=generate_id(IdPrefix.DEVICE),
            **payload.model_dump(),
            created_by=payload.last_updated_by,
            created_at=now,
            last_updated_at=now,
        )
        self._repository.save(device)
        return device

    def list_devices(
        self,
        page: int,
        page_size: int,
        brand_id: str | None = None,
        category_id: str | None = None,
    ) -> DevicePage:
        """Lọc và lấy một trang thiết bị từ repository."""

        items, total = self._repository.list_page(
            brand_id=brand_id,
            category_id=category_id,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
        return DevicePage(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size),
        )

    def list_available_devices(self) -> list[Device]:
        """Cung cấp inventory công khai cho application-layer orchestrator."""

        return self._repository.list()

    def get_device(self, device_id: str) -> Device:
        """Lấy một thiết bị hoặc phát sinh lỗi nghiệp vụ ánh xạ thành HTTP 404."""
        device = self._repository.get(device_id)
        if device is None:
            raise ResourceNotFoundError(f"Không tìm thấy device '{device_id}'")
        return device

    def get_device_by_hostname(self, hostname: str) -> Device:
        """Lấy Device theo hostname hoặc phát sinh lỗi ánh xạ thành HTTP 404."""

        device = self._repository.get_by_hostname(hostname)
        if device is None:
            raise ResourceNotFoundError(
                f"Không tìm thấy device có hostname '{hostname}'"
            )
        return device

    def update_device(self, device_id: str, payload: DeviceUpdate) -> Device:
        """Áp dụng PATCH và kiểm tra lại uniqueness trước khi lưu."""
        current = self.get_device(device_id)
        # exclude_unset phân biệt trường không gửi với trường chủ động gửi null.
        changes = payload.model_dump(exclude_unset=True)
        candidate = current.model_copy(update=changes)
        self._ensure_unique_device(
            candidate.hostname,
            candidate.host,
            candidate.port,
            exclude_device_id=device_id,
        )
        updated = candidate.model_copy(
            update={"last_updated_at": datetime.now(UTC)}
        )
        self._repository.save(updated)
        return updated

    def _ensure_unique_device(
        self,
        hostname: str,
        host: str,
        port: int,
        exclude_device_id: str | None = None,
    ) -> None:
        """Bảo vệ hai unique constraint trước khi repository ghi database.

        Kiểm tra ở service tạo thông báo lỗi dễ hiểu cho frontend. PostgreSQL vẫn
        giữ UNIQUE constraint như lớp bảo vệ cuối cùng khi có request đồng thời.
        """
        # Hai constraint này phản ánh trực tiếp thiết kế DB: hostname là duy nhất,
        # đồng thời một host/port không được ánh xạ cho hai thiết bị.
        for device in self._repository.list():
            if device.id == exclude_device_id:
                continue
            if device.hostname.casefold() == hostname.casefold():
                raise ResourceConflictError(
                    f"Hostname '{hostname}' đã được sử dụng"
                )
            if (device.host, device.port) == (host, port):
                raise ResourceConflictError(
                    f"Địa chỉ '{host}:{port}' đã được sử dụng"
                )
