"""Chuẩn hóa command cấu hình trước khi phê duyệt và thực thi."""

from ipaddress import IPv4Address, IPv4Network
import re


_SESSION_COMMANDS = {
    "configure terminal",
    "conf t",
    "end",
    "write memory",
    "wr mem",
    "copy running-config startup-config",
    "copy run start",
}
_INCOMPLETE_TARGETED_LDP = re.compile(
    r"^mpls\s+ldp\s+neighbor\s+\S+\s+targeted$",
    flags=re.IGNORECASE,
)
_IP_ADDRESS_COMMAND = re.compile(
    r"^ip\s+address\s+(\S+)\s+(\S+)(?:\s+secondary)?$",
    flags=re.IGNORECASE,
)
_SUBMODE_COMMAND = re.compile(
    r"^(?P<mode>interface|router|line|route-map|ip\s+access-list)\s+\S+",
    flags=re.IGNORECASE,
)
_INVALID_LDP_INTERFACE = re.compile(
    r"^mpls\s+ldp\s+interface(?:\s+\S+)?$",
    flags=re.IGNORECASE,
)
_GLOBAL_CONFIGURATION_COMMAND = re.compile(
    r"^(?:mpls\s+ldp\s+(?:router-id|neighbor)|ip\s+route)\b",
    flags=re.IGNORECASE,
)


def normalize_config_commands(commands: list[str]) -> list[str]:
    """Chỉ giữ payload cho ``send_config_set`` và chặn cú pháp đã biết là thiếu."""

    stripped_commands = [
        command.strip()
        for command in commands
        if command.strip().lower() not in _SESSION_COMMANDS
    ]
    if not stripped_commands:
        raise ValueError("Danh sách cấu hình không còn command hợp lệ sau chuẩn hóa")

    # Bước 1: Theo dõi configuration submode và tự thoát trước khi đổi context.
    normalized: list[str] = []
    active_submode: str | None = None
    for command in stripped_commands:
        lowered = command.casefold()
        if _INVALID_LDP_INTERFACE.fullmatch(command):
            raise ValueError(
                "Cisco IOS không hỗ trợ 'mpls ldp interface ...'; "
                "hãy dùng 'mpls ip' trong đúng interface submode"
            )

        submode_match = _SUBMODE_COMMAND.match(command)
        if submode_match is not None:
            if active_submode is not None and normalized[-1].casefold() != "exit":
                normalized.append("exit")
            normalized.append(command)
            active_submode = submode_match.group("mode").casefold()
            continue

        if lowered == "exit":
            if active_submode is not None:
                normalized.append(command)
                active_submode = None
            continue

        if active_submode is not None and _GLOBAL_CONFIGURATION_COMMAND.match(command):
            normalized.append("exit")
            active_submode = None

        if active_submode == "router" and lowered == "mpls ip":
            raise ValueError(
                "Command 'mpls ip' không hợp lệ trong router submode; "
                "hãy đặt command trong interface submode"
            )
        normalized.append(command)

    # Bước 2: Kiểm tra các dạng targeted LDP chưa hoàn chỉnh.
    incomplete_ldp = next(
        (command for command in normalized if _INCOMPLETE_TARGETED_LDP.fullmatch(command)),
        None,
    )
    if incomplete_ldp:
        raise ValueError(
            f"Command targeted LDP thiếu từ khóa cuối 'ldp': {incomplete_ldp}"
        )

    # Bước 3: Kiểm tra địa chỉ interface không phải network/broadcast address.
    for command in normalized:
        match = _IP_ADDRESS_COMMAND.fullmatch(command)
        if not match:
            continue

        try:
            address = IPv4Address(match.group(1))
            network = IPv4Network(f"{address}/{match.group(2)}", strict=False)
        except ValueError as error:
            raise ValueError(f"Command IP không hợp lệ: {command}") from error

        if network.prefixlen < 31 and address in {
            network.network_address,
            network.broadcast_address,
        }:
            address_kind = (
                "network" if address == network.network_address else "broadcast"
            )
            first_host = network.network_address + 1
            last_host = network.broadcast_address - 1
            raise ValueError(
                f"Địa chỉ {address} là địa chỉ {address_kind} của "
                f"{network.with_prefixlen}, không thể gán cho interface. "
                f"Host hợp lệ: {first_host}-{last_host}"
            )
    return normalized
