"""Kiểm thử tham số thực thi của các network backend."""

import pytest

from app.domains.execution.schemas import AccessMode
from app.tools.network.backends import NetmikoNetworkTool
from app.tools.network.commands import normalize_config_commands


class StubConnection:
    def __init__(self, config_output: str = "configured") -> None:
        self.config_call = None
        self.command_calls = []
        self.disconnected = False
        self.config_output = config_output
        self.saved = False

    def send_config_set(self, commands, **kwargs):
        self.config_call = (commands, kwargs)
        return self.config_output

    def send_command(self, command, **kwargs):
        self.command_calls.append((command, kwargs))
        return "output"

    def save_config(self):
        self.saved = True
        return "saved"

    def disconnect(self):
        self.disconnected = True


class StubNetworkService:
    def __init__(self, connection: StubConnection) -> None:
        self.connection = connection

    def connect(self, device_id: str):
        return {"success": True, "connection": self.connection}


def test_netmiko_write_uses_configured_read_timeout() -> None:
    connection = StubConnection()
    tool = NetmikoNetworkTool(StubNetworkService(connection), read_timeout=60)

    result = tool.execute("P3", AccessMode.WRITE, ["router ospf 1"])

    assert connection.config_call == (
        ["router ospf 1"],
        {"read_timeout": 60, "cmd_verify": False},
    )
    assert result[0].output == "configured"
    assert connection.saved is True
    assert connection.disconnected is True


def test_netmiko_write_reports_cli_error_when_echo_verification_is_disabled() -> None:
    connection = StubConnection(
        "router ospf 1\n% Invalid input detected at '^' marker."
    )
    tool = NetmikoNetworkTool(StubNetworkService(connection), read_timeout=60)

    try:
        tool.execute("P3", AccessMode.WRITE, ["router ospf 1"])
    except RuntimeError as error:
        assert "Thiết bị từ chối lệnh cấu hình" in str(error)
        assert "router ospf 1" in str(error)
    else:
        raise AssertionError("CLI error phải làm thao tác cấu hình thất bại")

    assert connection.disconnected is True
    assert connection.saved is False


def test_netmiko_read_uses_configured_read_timeout() -> None:
    connection = StubConnection()
    tool = NetmikoNetworkTool(StubNetworkService(connection), read_timeout=60)

    tool.execute("P3", AccessMode.READ, ["show ip route"])

    assert connection.command_calls == [
        ("show ip route", {"read_timeout": 60}),
    ]
    assert connection.disconnected is True


def test_normalize_config_commands_removes_session_commands() -> None:
    commands = normalize_config_commands(
        [
            "configure terminal",
            "interface GigabitEthernet0/0",
            "mpls ip",
            "exit",
            "end",
            "write memory",
        ]
    )

    assert commands == ["interface GigabitEthernet0/0", "mpls ip", "exit"]


def test_normalize_config_commands_rejects_incomplete_targeted_ldp() -> None:
    with pytest.raises(ValueError, match="thiếu từ khóa cuối 'ldp'"):
        normalize_config_commands(["mpls ldp neighbor 10.0.13.1 targeted"])


@pytest.mark.parametrize(
    "address",
    ["10.0.34.0", "10.0.34.3"],
)
def test_normalize_config_commands_rejects_network_and_broadcast_address(
    address: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=r"Host hợp lệ: 10\.0\.34\.1-10\.0\.34\.2",
    ):
        normalize_config_commands(
            [f"ip address {address} 255.255.255.252"]
        )


def test_normalize_config_commands_accepts_usable_30_host() -> None:
    command = "ip address 10.0.34.2 255.255.255.252"

    assert normalize_config_commands([command]) == [command]
