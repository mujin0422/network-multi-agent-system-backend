"""Parser OSPF, MPLS/LDP, BGP, route và ACL."""

import re
from collections.abc import Callable

from app.diagnostics.parsers.common import clean_lines, interface_resource, node_resource
from app.diagnostics.schemas import DiagnosticEvidence, EvidenceSource, EvidenceType


def _evidence(
    kind: EvidenceType,
    source: EvidenceSource,
    output: str,
    attributes: dict,
    lines: list[str],
    resource: str | None = None,
) -> DiagnosticEvidence:
    return DiagnosticEvidence(
        evidence_type=kind,
        resource_id=resource or node_resource(source.device_name),
        source=source,
        attributes=attributes,
        supporting_lines=lines,
        raw_output=output,
    )


def parse_ospf(
    command: str, output: str, source: EvidenceSource
) -> list[DiagnosticEvidence]:
    lines = clean_lines(output)
    if "ospf interface" in command.casefold():
        return _parse_ospf_interfaces(command, lines, output, source)
    network_lines = [line for line in lines if line.casefold().startswith("network ")]
    result: list[DiagnosticEvidence] = []
    if network_lines or "running-config" in command.casefold():
        result.append(
            _evidence(
                EvidenceType.OSPF_CONFIG,
                source,
                output,
                {
                    "network_statements": network_lines,
                    "process_present": any(
                        line.casefold().startswith("router ospf ") for line in lines
                    ),
                },
                network_lines or lines[:3],
            )
        )
    if "ospf neighbor" in command.casefold():
        neighbors = [
            line for line in lines if re.match(r"^\d+\.\d+\.\d+\.\d+\s+\d+\s+\S+", line)
        ]
        result.append(
            _evidence(
                EvidenceType.OSPF_NEIGHBOR,
                source,
                output,
                {
                    "neighbor_count": len(neighbors),
                    "neighbors": neighbors,
                },
                neighbors,
            )
        )
    return result


def _parse_ospf_interfaces(
    command: str,
    lines: list[str],
    output: str,
    source: EvidenceSource,
) -> list[DiagnosticEvidence]:
    """Bóc từng interface OSPF để area luôn gắn với đúng resource."""

    starts = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^\S+ is (?:up|down|administratively down), line protocol is", line, re.IGNORECASE)
    ]
    if not starts:
        requested = re.search(r"ospf interface\s+(\S+)", command, re.IGNORECASE)
        area = next(
            (
                match.group(1)
                for line in lines
                if (match := re.search(r"\bArea\s+(\S+)", line, re.IGNORECASE))
            ),
            None,
        )
        if requested and area is not None:
            interface = requested.group(1)
            return [
                _evidence(
                    EvidenceType.OSPF_CONFIG,
                    source,
                    output,
                    {
                        "interface": interface,
                        "area": area.rstrip(","),
                        "ip_prefix": None,
                        "process_id": None,
                        "network_type": None,
                        "neighbor_count": None,
                        "adjacent_neighbor_count": None,
                    },
                    lines[:3],
                    interface_resource(source.device_name, interface),
                )
            ]
    result: list[DiagnosticEvidence] = []
    for position, start in enumerate(starts):
        block = lines[start : starts[position + 1] if position + 1 < len(starts) else len(lines)]
        interface = block[0].split(maxsplit=1)[0]
        internet = next(
            (line for line in block if "internet address" in line.casefold()),
            "",
        )
        process = next(
            (line for line in block if line.casefold().startswith("process id ")),
            "",
        )
        area_match = re.search(r"\bArea\s+(\S+)", internet, re.IGNORECASE)
        address_match = re.search(
            r"Internet Address\s+(\d+\.\d+\.\d+\.\d+/\d+)",
            internet,
            re.IGNORECASE,
        )
        process_match = re.search(r"Process ID\s+(\d+)", process, re.IGNORECASE)
        network_type_match = re.search(
            r"Network Type\s+([^,]+)", process, re.IGNORECASE
        )
        neighbor_match = next(
            (
                re.search(
                    r"Neighbor Count is\s+(\d+),\s+Adjacent neighbor count is\s+(\d+)",
                    line,
                    re.IGNORECASE,
                )
                for line in block
                if "neighbor count is" in line.casefold()
            ),
            None,
        )
        result.append(
            _evidence(
                EvidenceType.OSPF_CONFIG,
                source,
                output,
                {
                    "interface": interface,
                    "area": area_match.group(1) if area_match else None,
                    "ip_prefix": address_match.group(1) if address_match else None,
                    "process_id": int(process_match.group(1)) if process_match else None,
                    "network_type": (
                        network_type_match.group(1).strip()
                        if network_type_match
                        else None
                    ),
                    "neighbor_count": (
                        int(neighbor_match.group(1)) if neighbor_match else None
                    ),
                    "adjacent_neighbor_count": (
                        int(neighbor_match.group(2)) if neighbor_match else None
                    ),
                },
                [line for line in (block[0], internet, process) if line],
                interface_resource(source.device_name, interface),
            )
        )
    return result


def parse_mpls(
    command: str, output: str, source: EvidenceSource
) -> list[DiagnosticEvidence]:
    lines = clean_lines(output)
    if "ldp neighbor" in command.casefold():
        peers = [
            line
            for line in lines
            if "peer ldp ident" in line.casefold()
            or "tcp connection" in line.casefold()
        ]
        return [
            _evidence(
                EvidenceType.LDP_NEIGHBOR,
                source,
                output,
                {"neighbor_count": len(peers), "neighbors": peers},
                peers,
            )
        ]
    entries = [
        line
        for line in lines
        if re.match(
            r"^(?:Fa|Gi|Te|Et|FastEthernet|GigabitEthernet)\S+\s+", line, re.IGNORECASE
        )
    ]
    parsed_interfaces: list[dict[str, str | bool]] = []
    for entry in entries:
        columns = entry.split()
        if not columns:
            continue
        parsed_interfaces.append(
            {
                "interface": columns[0],
                "mpls_enabled": len(columns) > 1
                and columns[1].casefold() == "yes",
                "operational": columns[-1].casefold() == "yes",
            }
        )
    return [
        _evidence(
            EvidenceType.MPLS_INTERFACE,
            source,
            output,
            {
                "interface_count": len(entries),
                "interfaces": entries,
                "interface_states": parsed_interfaces,
            },
            entries,
        )
    ]


def parse_bgp(
    command: str, output: str, source: EvidenceSource
) -> list[DiagnosticEvidence]:
    lines = clean_lines(output)
    if "running-config" in command.casefold():
        neighbors = [line for line in lines if line.casefold().startswith("neighbor ")]
        shutdown = [line for line in neighbors if line.casefold().endswith(" shutdown")]
        return [
            _evidence(
                EvidenceType.BGP_CONFIG,
                source,
                output,
                {"neighbors": neighbors, "shutdown_neighbors": shutdown},
                neighbors,
            )
        ]
    rows = [
        line for line in lines if re.match(r"^\d+\.\d+\.\d+\.\d+\s+\d+\s+\d+", line)
    ]
    return [
        _evidence(
            EvidenceType.BGP_NEIGHBOR,
            source,
            output,
            {"neighbor_count": len(rows), "neighbors": rows},
            rows,
        )
    ]


def parse_route(
    command: str, output: str, source: EvidenceSource
) -> list[DiagnosticEvidence]:
    lines = clean_lines(output)
    routes = [
        line
        for line in lines
        if re.match(r"^(?:[A-Z*]+\s+)?(?:\d+\.\d+\.\d+\.\d+|0\.0\.0\.0)", line)
        or line.casefold().startswith("ip route ")
    ]
    gateway = next(
        (line for line in lines if "gateway of last resort" in line.casefold()), None
    )
    has_default_entry = any(
        re.search(
            r"(?:^|\s)(?:0\.0\.0\.0(?:/0|\s+0\.0\.0\.0)|0\.0\.0\.0/0)(?:\s|$)", line
        )
        for line in routes
    )
    return [
        _evidence(
            EvidenceType.ROUTE,
            source,
            output,
            {
                "route_count": len(routes),
                "routes": routes,
                "default_route_present": bool(
                    gateway and "not set" not in gateway.casefold()
                )
                or has_default_entry,
            },
            ([gateway] if gateway else []) + routes,
        )
    ]


def parse_acl(
    command: str, output: str, source: EvidenceSource
) -> list[DiagnosticEvidence]:
    lines = clean_lines(output)
    entries = [
        line for line in lines if re.search(r"\b(?:permit|deny)\b", line, re.IGNORECASE)
    ]
    return [
        _evidence(
            EvidenceType.ACL,
            source,
            output,
            {"entry_count": len(entries), "entries": entries},
            entries,
        )
    ]


PARSER_BY_NAME: dict[
    str, Callable[[str, str, EvidenceSource], list[DiagnosticEvidence]]
] = {
    "ospf": parse_ospf,
    "mpls": parse_mpls,
    "bgp": parse_bgp,
    "route": parse_route,
    "acl": parse_acl,
}
