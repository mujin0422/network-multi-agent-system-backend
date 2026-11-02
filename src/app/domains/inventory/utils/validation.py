"""Các hàm kiểm tra uniqueness dùng chung trong Inventory domain."""

from collections.abc import Iterable
from typing import Protocol

from app.core.exceptions import ResourceConflictError
from app.domains.inventory.schemas import Device


class NamedResource(Protocol):
    """Kiểu tối thiểu của resource có ID và tên cần kiểm tra."""

    id: str
    name: str


def ensure_unique_name(
    resources: Iterable[NamedResource],
    name: str,
    *,
    resource_label: str,
    exclude_id: str | None = None,
) -> None:
    """Báo conflict khi tên resource đã tồn tại, không phân biệt hoa thường."""

    normalized_name = name.casefold()
    for resource in resources:
        if resource.id == exclude_id:
            continue
        if resource.name.casefold() == normalized_name:
            raise ResourceConflictError(
                f"Tên {resource_label} '{name}' đã được sử dụng"
            )


def ensure_unique_device(
    devices: Iterable[Device],
    hostname: str,
    host: str,
    port: int,
    *,
    exclude_device_id: str | None = None,
) -> None:
    """Kiểm tra unique hostname và cặp host/port trước khi ghi Device."""

    normalized_hostname = hostname.casefold()
    for device in devices:
        if device.id == exclude_device_id:
            continue
        if device.hostname.casefold() == normalized_hostname:
            raise ResourceConflictError(
                f"Hostname '{hostname}' đã được sử dụng"
            )
        if (device.host, device.port) == (host, port):
            raise ResourceConflictError(
                f"Địa chỉ '{host}:{port}' đã được sử dụng"
            )
