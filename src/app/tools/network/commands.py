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


def normalize_config_commands(commands: list[str]) -> list[str]:
    """Chỉ giữ payload cho ``send_config_set`` và chặn cú pháp đã biết là thiếu."""

    normalized = [
        command.strip()
        for command in commands
        if command.strip().lower() not in _SESSION_COMMANDS
    ]
    if not normalized:
        raise ValueError("Danh sách cấu hình không còn command hợp lệ sau chuẩn hóa")

    incomplete_ldp = next(
        (command for command in normalized if _INCOMPLETE_TARGETED_LDP.fullmatch(command)),
        None,
    )
    if incomplete_ldp:
        raise ValueError(
            f"Command targeted LDP thiếu từ khóa cuối 'ldp': {incomplete_ldp}"
        )

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
