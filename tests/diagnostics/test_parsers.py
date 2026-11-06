"""Kiểm tra chuyển CLI output thành evidence có cấu trúc."""

from app.diagnostics import EvidenceSource, EvidenceType, parse_command_output


def source(command: str) -> EvidenceSource:
    return EvidenceSource(
        execution_id="opdv-test",
        device_id="devc-p3",
        device_name="P3",
        command=command,
    )


def test_parse_interface_status_and_shutdown_config() -> None:
    status_command = "show interfaces FastEthernet2/0"
    status = parse_command_output(
        status_command,
        "FastEthernet2/0 is administratively down, line protocol is down",
        source(status_command),
    )
    assert status[0].evidence_type == EvidenceType.INTERFACE_STATUS
    assert status[0].resource_id == "interface/p3/fastethernet2/0"
    assert status[0].attributes["administratively_down"] is True

    config_command = "show running-config interface FastEthernet2/0"
    config = parse_command_output(
        config_command,
        "interface FastEthernet2/0\n ip address 10.0.36.3 255.255.255.0\n shutdown",
        source(config_command),
    )
    config_evidence = next(
        item for item in config if item.evidence_type == EvidenceType.INTERFACE_CONFIG
    )
    ip_evidence = next(
        item for item in config if item.evidence_type == EvidenceType.IP_CONFIGURATION
    )
    assert config_evidence.attributes["configured_shutdown"] is True
    assert ip_evidence.attributes["subnet_mask"] == "255.255.255.0"


def test_parse_ospf_config_and_empty_neighbor_table() -> None:
    config_command = "show running-config | section router ospf"
    config = parse_command_output(
        config_command,
        "router ospf 1\n network 10.0.34.0 0.0.0.255 area 0",
        source(config_command),
    )
    assert config[0].evidence_type == EvidenceType.OSPF_CONFIG
    assert config[0].attributes["process_present"] is True

    neighbor_command = "show ip ospf neighbor"
    neighbors = parse_command_output(neighbor_command, "", source(neighbor_command))
    assert neighbors[0].evidence_type == EvidenceType.OSPF_NEIGHBOR
    assert neighbors[0].attributes["neighbor_count"] == 0


def test_parse_unknown_command_preserves_raw_output() -> None:
    command = "show clock"
    evidence = parse_command_output(command, "12:00:00 UTC", source(command))
    assert evidence[0].evidence_type == EvidenceType.UNKNOWN
    assert evidence[0].raw_output == "12:00:00 UTC"
