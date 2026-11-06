"""Tự động chọn parser theo command và trả evidence có cấu trúc."""

from app.diagnostics.parsers.interface import parse_interface
from app.diagnostics.parsers.protocols import PARSER_BY_NAME
from app.diagnostics.schemas import DiagnosticEvidence, EvidenceSource, EvidenceType
from app.diagnostics.parsers.common import node_resource


def _parser_name(command: str) -> str | None:
    normalized = command.strip().casefold()
    if "interface" in normalized:
        return "interface"
    if "ospf" in normalized:
        return "ospf"
    if "mpls" in normalized or "ldp" in normalized:
        return "mpls"
    if "bgp" in normalized:
        return "bgp"
    if "route" in normalized or "gateway" in normalized:
        return "route"
    if "access-list" in normalized or "access list" in normalized:
        return "acl"
    return None


def parse_command_output(
    command: str, output: str, source: EvidenceSource
) -> list[DiagnosticEvidence]:
    """Parse output theo command; output không hỗ trợ vẫn được giữ dạng UNKNOWN."""
    name = _parser_name(command)
    if name == "interface":
        parsed = parse_interface(command, output, source)
    elif name is not None:
        parsed = PARSER_BY_NAME[name](command, output, source)
    else:
        parsed = []
    if parsed:
        return parsed
    return [
        DiagnosticEvidence(
            evidence_type=EvidenceType.UNKNOWN,
            resource_id=node_resource(source.device_name),
            source=source,
            attributes={"parser_supported": name is not None},
            supporting_lines=[],
            raw_output=output,
        )
    ]


__all__ = ["parse_command_output"]
