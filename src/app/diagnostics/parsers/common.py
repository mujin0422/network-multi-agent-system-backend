"""Tiện ích chung cho các CLI parser thuần hàm."""

import re


def clean_lines(output: str) -> list[str]:
    """Loại dòng rỗng và prompt/command echo khỏi output thiết bị."""
    return [line.strip() for line in output.splitlines() if line.strip()]


def normalize_resource_part(value: str) -> str:
    """Chuẩn hóa thành phần resource ID mà không làm mất số cổng."""
    return re.sub(r"\s+", "", value.strip().casefold())


def interface_resource(device_name: str, interface: str) -> str:
    return f"interface/{normalize_resource_part(device_name)}/{normalize_resource_part(interface)}"


def node_resource(device_name: str) -> str:
    return f"node/{normalize_resource_part(device_name)}"
