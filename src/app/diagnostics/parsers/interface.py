"""Parser trạng thái, cấu hình và địa chỉ interface Cisco IOS."""

import ipaddress
import re

from app.diagnostics.parsers.common import clean_lines, interface_resource
from app.diagnostics.schemas import DiagnosticEvidence, EvidenceSource, EvidenceType

_STATUS = re.compile(
    r"^(?P<interface>\S+) is (?P<admin>administratively down|up|down|reset), "
    r"line protocol is (?P<oper>up|down|administratively down)",
    re.IGNORECASE,
)
_BRIEF = re.compile(
    r"^(?P<interface>\S+)\s+(?P<ip>\S+)\s+\S+\s+\S+\s+"
    r"(?P<status>administratively down|up|down)\s+(?P<protocol>up|down)$",
    re.IGNORECASE,
)
_INTERNET_ADDRESS = re.compile(
    r"^Internet address is (?P<address>\d+\.\d+\.\d+\.\d+)/(?P<prefix>\d+)$",
    re.IGNORECASE,
)


def parse_interface(
    command: str, output: str, source: EvidenceSource
) -> list[DiagnosticEvidence]:
    """Parse show interfaces, show ip interface brief và interface config."""
    lines = clean_lines(output)
    evidence: list[DiagnosticEvidence] = []
    for line in lines:
        match = _STATUS.match(line)
        if match:
            admin = match.group("admin").casefold()
            evidence.append(
                DiagnosticEvidence(
                    evidence_type=EvidenceType.INTERFACE_STATUS,
                    resource_id=interface_resource(
                        source.device_name, match.group("interface")
                    ),
                    source=source,
                    attributes={
                        "interface": match.group("interface"),
                        "admin_status": "DOWN" if admin != "up" else "UP",
                        "oper_status": match.group("oper").upper(),
                        "administratively_down": admin == "administratively down",
                    },
                    supporting_lines=[line],
                    raw_output=output,
                )
            )
            continue
        brief = _BRIEF.match(line)
        if brief:
            attributes = {
                "interface": brief.group("interface"),
                "ip_address": None
                if brief.group("ip").casefold() == "unassigned"
                else brief.group("ip"),
                "admin_status": "UP"
                if brief.group("status").casefold() == "up"
                else "DOWN",
                "oper_status": brief.group("protocol").upper(),
                "administratively_down": brief.group("status").casefold()
                == "administratively down",
            }
            resource = interface_resource(source.device_name, brief.group("interface"))
            evidence.append(
                DiagnosticEvidence(
                    evidence_type=EvidenceType.INTERFACE_STATUS,
                    resource_id=resource,
                    source=source,
                    attributes=attributes,
                    supporting_lines=[line],
                    raw_output=output,
                )
            )

    # `show interfaces X` chứa IP dạng CIDR; giữ nó thành evidence cấu hình để
    # đối chiếu mask hai đầu ngay cả khi Planner không gọi running-config.
    status_evidence = next(
        (
            item
            for item in evidence
            if item.evidence_type == EvidenceType.INTERFACE_STATUS
        ),
        None,
    )
    internet_line = next(
        (line for line in lines if _INTERNET_ADDRESS.match(line)),
        None,
    )
    if status_evidence is not None and internet_line is not None:
        address_match = _INTERNET_ADDRESS.match(internet_line)
        if address_match is not None:
            address = address_match.group("address")
            prefix = int(address_match.group("prefix"))
            netmask = str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)
            evidence.append(
                DiagnosticEvidence(
                    evidence_type=EvidenceType.IP_CONFIGURATION,
                    resource_id=status_evidence.resource_id,
                    source=source,
                    attributes={
                        "interface": status_evidence.attributes.get("interface"),
                        "ip_address": address,
                        "subnet_mask": netmask,
                        "prefix_length": prefix,
                    },
                    supporting_lines=[internet_line],
                    raw_output=output,
                )
            )

    interface_line = next(
        (line for line in lines if line.casefold().startswith("interface ")), None
    )
    if interface_line:
        interface = interface_line.split(maxsplit=1)[1]
        shutdown = any(line.casefold() == "shutdown" for line in lines)
        ip_line = next(
            (line for line in lines if line.casefold().startswith("ip address ")), None
        )
        access_group = next(
            (line for line in lines if line.casefold().startswith("ip access-group ")),
            None,
        )
        attributes: dict[str, str | bool | None] = {
            "interface": interface,
            "configured_shutdown": shutdown,
            "mpls_enabled": any(line.casefold() == "mpls ip" for line in lines),
            "access_group": access_group,
        }
        if ip_line:
            parts = ip_line.split()
            attributes.update(
                {
                    "ip_address": parts[2],
                    "subnet_mask": parts[3] if len(parts) > 3 else None,
                }
            )
        supporting = [
            line
            for line in lines
            if line == interface_line
            or line.casefold() in {"shutdown", "no shutdown", "mpls ip"}
            or line.casefold().startswith(("ip address ", "ip access-group "))
        ]
        resource = interface_resource(source.device_name, interface)
        evidence.append(
            DiagnosticEvidence(
                evidence_type=EvidenceType.INTERFACE_CONFIG,
                resource_id=resource,
                source=source,
                attributes=attributes,
                supporting_lines=supporting,
                raw_output=output,
            )
        )
        if ip_line:
            evidence.append(
                DiagnosticEvidence(
                    evidence_type=EvidenceType.IP_CONFIGURATION,
                    resource_id=resource,
                    source=source,
                    attributes={
                        "interface": interface,
                        "ip_address": attributes["ip_address"],
                        "subnet_mask": attributes["subnet_mask"],
                    },
                    supporting_lines=[ip_line],
                    raw_output=output,
                )
            )
        if access_group:
            evidence.append(
                DiagnosticEvidence(
                    evidence_type=EvidenceType.ACL,
                    resource_id=resource,
                    source=source,
                    attributes={"attachment": access_group},
                    supporting_lines=[access_group],
                    raw_output=output,
                )
            )
    return evidence
