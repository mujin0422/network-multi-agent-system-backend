"""Public service của Network Inventory domain."""

from datetime import UTC, datetime

from app.core.errors import ResourceConflictError, ResourceNotFoundError
from app.core.ids import generate_id
from app.domains.inventory.repository import DeviceRepository
from app.domains.inventory.schemas import Device, DeviceCreate, DeviceUpdate


class InventoryService:
    def __init__(self, repository: DeviceRepository) -> None:
        self._repository = repository

    def create_device(self, payload: DeviceCreate) -> Device:
        self._ensure_unique_device(payload.hostname, payload.host, payload.port)
        now = datetime.now(UTC)
        device = Device(
            id=generate_id("devc"),
            **payload.model_dump(),
            created_at=now,
            last_updated_at=now,
        )
        self._repository.save(device)
        return device

    def list_devices(self) -> list[Device]:
        return self._repository.list()

    def get_device(self, device_id: str) -> Device:
        device = self._repository.get(device_id)
        if device is None:
            raise ResourceNotFoundError(f"Không tìm thấy device '{device_id}'")
        return device

    def update_device(self, device_id: str, payload: DeviceUpdate) -> Device:
        current = self.get_device(device_id)
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
