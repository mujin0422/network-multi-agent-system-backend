"""Kiểm tra quan hệ nhân quả giữa kết luận Analyst và evidence đã quan sát."""

import ipaddress
import re
from enum import StrEnum

from pydantic import BaseModel, Field

from app.diagnostics.parsers.common import normalize_resource_part
from app.diagnostics.schemas import DiagnosticEvidence, EvidenceType
from app.domains.evaluation.schemas import FaultType, PredictedRootCause


class CausalClaimStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    SUSPECTED = "SUSPECTED"


class CausalEvidenceReference(BaseModel):
    """Tham chiếu tối thiểu tới evidence thực tế dùng để xét một kết luận."""

    execution_id: str
    evidence_type: EvidenceType
    resource_id: str
    device_name: str
    command: str
    supporting_lines: list[str] = Field(default_factory=list)


class CausalReadCheck(BaseModel):
    """READ check do matcher đề nghị khi thiếu evidence theo topology."""

    device: str
    commands: list[str] = Field(min_length=1, max_length=4)
    reason: str


class CausalClaimDecision(BaseModel):
    """Kết quả xác nhận một root cause do Analyst đề xuất."""

    cause: PredictedRootCause
    status: CausalClaimStatus
    reason: str
    evidence: list[CausalEvidenceReference] = Field(default_factory=list)
    missing_evidence: list[EvidenceType] = Field(default_factory=list)
    recommended_checks: list[CausalReadCheck] = Field(default_factory=list)


class CausalGateResult(BaseModel):
    """Tập root cause được xác nhận và các giả thuyết chưa đủ bằng chứng."""

    confirmed: list[PredictedRootCause] = Field(default_factory=list)
    suspected: list[PredictedRootCause] = Field(default_factory=list)
    decisions: list[CausalClaimDecision] = Field(default_factory=list)


class CausalScope(BaseModel):
    """Phạm vi thiết bị/interface được nêu trong yêu cầu và topology liên quan."""

    primary_devices: set[str] = Field(default_factory=set)
    primary_interfaces: set[str] = Field(default_factory=set)
    topology_neighbors: dict[str, list[dict[str, str]]] = Field(default_factory=dict)


def build_causal_scope(
    user_message: str,
    device_names: list[str],
    topology_neighbors: dict[str, list[dict[str, str]]] | None = None,
) -> CausalScope:
    """Bóc phạm vi được người dùng nêu mà không suy đoán thêm thiết bị lỗi."""

    message = user_message.casefold()
    devices = {
        normalize_resource_part(name)
        for name in device_names
        if re.search(
            rf"(?<![\w-]){re.escape(name.casefold())}(?![\w-])",
            message,
        )
    }
    interfaces = {
        _normalize_interface(match.group(0))
        for match in re.finditer(
            r"\b(?:FastEthernet|GigabitEthernet|TenGigabitEthernet|Loopback|Fa|Gi|Te|Lo)\d+(?:/\d+){0,2}\b",
            user_message,
            re.IGNORECASE,
        )
    }
    return CausalScope(
        primary_devices=devices,
        primary_interfaces=interfaces,
        topology_neighbors=topology_neighbors or {},
    )


def evaluate_causal_claims(
    causes: list[PredictedRootCause],
    evidence: list[DiagnosticEvidence],
    scope: CausalScope | None = None,
) -> CausalGateResult:
    """Chỉ xác nhận root cause khi evidence thỏa quy tắc của loại lỗi."""

    normalized_causes = [_normalize_claim_scope(cause, scope) for cause in causes]
    decisions = [_evaluate_claim(cause, evidence, scope) for cause in normalized_causes]
    return CausalGateResult(
        confirmed=[
            item.cause
            for item in decisions
            if item.status == CausalClaimStatus.CONFIRMED
        ],
        suspected=[
            item.cause
            for item in decisions
            if item.status == CausalClaimStatus.SUSPECTED
        ],
        decisions=decisions,
    )


def _normalize_claim_scope(
    cause: PredictedRootCause,
    scope: CausalScope | None,
) -> PredictedRootCause:
    """Giữ RCA ở mức node khi yêu cầu OSPF không khoanh một interface cụ thể."""

    if (
        cause.fault_type == FaultType.OSPF_AREA_MISMATCH
        and cause.interface is not None
        and scope is not None
        and not scope.primary_interfaces
    ):
        return cause.model_copy(update={"interface": None})
    return cause


def _evaluate_claim(
    cause: PredictedRootCause,
    evidence: list[DiagnosticEvidence],
    scope: CausalScope | None,
) -> CausalClaimDecision:
    scope_rejection = _scope_rejection(cause, scope)
    if scope_rejection is not None:
        return CausalClaimDecision(
            cause=cause,
            status=CausalClaimStatus.SUSPECTED,
            reason=scope_rejection,
        )
    device_evidence = [
        item
        for item in evidence
        if normalize_resource_part(item.source.device_name)
        == normalize_resource_part(cause.device)
    ]
    interface_evidence = [
        item for item in device_evidence if _matches_interface(item, cause.interface)
    ]
    fault = cause.fault_type

    if fault in {FaultType.LINK_DOWN, FaultType.LOOPBACK_ADMIN_DOWN}:
        matched = [
            item
            for item in interface_evidence
            if (
                item.evidence_type == EvidenceType.INTERFACE_STATUS
                and (
                    "brief" not in item.source.command.casefold()
                    or (
                        item.attributes.get("ip_address") is not None
                        or any(
                            observed.evidence_type == EvidenceType.IP_CONFIGURATION
                            for observed in interface_evidence
                        )
                    )
                )
                and (
                    item.attributes.get("administratively_down") is True
                    or item.attributes.get("oper_status") == "DOWN"
                )
            )
            or (
                item.evidence_type == EvidenceType.INTERFACE_CONFIG
                and item.attributes.get("configured_shutdown") is True
                and item.attributes.get("ip_address") is not None
            )
        ]
        return _decision(
            cause, matched, "Interface được quan sát ở trạng thái down hoặc shutdown."
        )

    if fault == FaultType.MPLS_DISABLED:
        status_observations = [
            item
            for item in interface_evidence
            if item.evidence_type == EvidenceType.INTERFACE_STATUS
        ]
        up_statuses = [
            item
            for item in status_observations
            if item.attributes.get("admin_status") == "UP"
            and item.attributes.get("oper_status") == "UP"
        ]
        config_observations = [
            item
            for item in interface_evidence
            if item.evidence_type == EvidenceType.INTERFACE_CONFIG
        ]
        disabled_configs = [
            item
            for item in config_observations
            if item.attributes.get("mpls_enabled") is False
        ]
        mpls_tables = [
            item
            for item in device_evidence
            if item.evidence_type == EvidenceType.MPLS_INTERFACE
        ]
        mpls_disabled = [
            item
            for item in mpls_tables
            if _mpls_interface_disabled(item, cause.interface)
        ]
        missing: list[EvidenceType] = []
        if not status_observations:
            missing.append(EvidenceType.INTERFACE_STATUS)
        if not config_observations:
            missing.append(EvidenceType.INTERFACE_CONFIG)
        if not mpls_tables:
            missing.append(EvidenceType.MPLS_INTERFACE)
        matched = [*up_statuses, *disabled_configs, *mpls_disabled]
        if up_statuses and disabled_configs and mpls_disabled:
            return _decision(
                cause,
                matched,
                "Interface đang up/up, thiếu lệnh mpls ip và không hoạt động trong bảng MPLS.",
            )
        return _decision(
            cause,
            [],
            "Chưa đủ bằng chứng theo interface để xác nhận MPLS bị tắt.",
            missing_evidence=missing,
        )

    if fault == FaultType.DEFAULT_ROUTE_MISSING:
        matched = [
            item
            for item in device_evidence
            if item.evidence_type == EvidenceType.ROUTE
            and item.attributes.get("default_route_present") is False
        ]
        return _decision(
            cause, matched, "Bảng định tuyến xác nhận không có default route."
        )

    if fault == FaultType.BGP_NEIGHBOR_ADMIN_DOWN:
        matched = [
            item
            for item in device_evidence
            if item.evidence_type == EvidenceType.BGP_CONFIG
            and bool(item.attributes.get("shutdown_neighbors"))
        ]
        return _decision(
            cause, matched, "Cấu hình BGP chứa neighbor ở trạng thái shutdown."
        )

    if fault == FaultType.ACL_TRAFFIC_BLOCK:
        attachments = [
            item
            for item in interface_evidence
            if item.evidence_type in {EvidenceType.INTERFACE_CONFIG, EvidenceType.ACL}
            and bool(
                item.attributes.get("access_group") or item.attributes.get("attachment")
            )
        ]
        deny_rules = [
            item
            for item in device_evidence
            if item.evidence_type == EvidenceType.ACL
            and any(
                "deny" in str(entry).casefold()
                for entry in item.attributes.get("entries", [])
            )
        ]
        matched = [*attachments, *deny_rules] if attachments and deny_rules else []
        return _decision(
            cause, matched, "ACL deny được quan sát và ACL được gắn trên interface."
        )

    if fault == FaultType.OSPF_NETWORK_MISSING:
        configs = [
            item
            for item in device_evidence
            if item.evidence_type == EvidenceType.OSPF_CONFIG
            and item.attributes.get("process_present") is True
        ]
        neighbors = [
            item
            for item in device_evidence
            if item.evidence_type == EvidenceType.OSPF_NEIGHBOR
            and item.attributes.get("neighbor_count") == 0
        ]
        matched = [*configs, *neighbors] if configs and neighbors else []
        return _decision(
            cause, matched, "Đã kiểm tra cấu hình OSPF và xác nhận không có adjacency."
        )

    if fault == FaultType.OSPF_AREA_MISMATCH:
        return _evaluate_ospf_area_mismatch(cause, evidence, scope)

    if fault in {FaultType.WRONG_IP_ADDRESS, FaultType.WRONG_SUBNET_MASK}:
        ip_evidence = [
            item
            for item in evidence
            if item.evidence_type == EvidenceType.IP_CONFIGURATION
        ]
        mismatched = _mismatched_ip_configuration(
            ip_evidence,
            fault,
            cause,
            scope,
        )
        matched = [item for item in mismatched if item in interface_evidence]
        if matched:
            matched.extend(item for item in mismatched if item not in matched)
        return _decision(
            cause,
            matched,
            "Địa chỉ và subnet mask hai đầu không tạo cùng mạng kết nối.",
        )

    return _decision(cause, [], "Chưa có quy tắc causal evidence cho loại lỗi này.")


def _scope_rejection(
    cause: PredictedRootCause,
    scope: CausalScope | None,
) -> str | None:
    if scope is None:
        return None
    device = normalize_resource_part(cause.device)
    if scope.primary_devices and device not in scope.primary_devices:
        return "Thiết bị không nằm trong phạm vi sự cố được nêu trong yêu cầu."
    if (
        cause.interface is not None
        and scope.primary_interfaces
        and _normalize_interface(cause.interface) not in scope.primary_interfaces
    ):
        return "Interface không nằm trong phạm vi sự cố được nêu trong yêu cầu."
    return None


def _decision(
    cause: PredictedRootCause,
    matched: list[DiagnosticEvidence],
    confirmed_reason: str,
    *,
    missing_evidence: list[EvidenceType] | None = None,
    recommended_checks: list[CausalReadCheck] | None = None,
) -> CausalClaimDecision:
    if matched:
        return CausalClaimDecision(
            cause=cause,
            status=CausalClaimStatus.CONFIRMED,
            reason=confirmed_reason,
            evidence=[_reference(item) for item in matched],
        )
    return CausalClaimDecision(
        cause=cause,
        status=CausalClaimStatus.SUSPECTED,
        reason=confirmed_reason
        if missing_evidence is not None
        else "Chưa có evidence trực tiếp đáp ứng quy tắc xác nhận nguyên nhân.",
        missing_evidence=missing_evidence or [],
        recommended_checks=recommended_checks or [],
    )


def _mpls_interface_disabled(
    item: DiagnosticEvidence,
    interface: str | None,
) -> bool:
    """Xác nhận interface vắng mặt hoặc được MPLS báo không operational."""

    if interface is None:
        return False
    expected = _normalize_interface(interface)
    states = item.attributes.get("interface_states", [])
    if not isinstance(states, list):
        return False
    matching = [
        state
        for state in states
        if isinstance(state, dict)
        and _normalize_interface(str(state.get("interface", ""))) == expected
    ]
    if not matching:
        return True
    return any(
        state.get("mpls_enabled") is False or state.get("operational") is False
        for state in matching
    )


def _reference(item: DiagnosticEvidence) -> CausalEvidenceReference:
    return CausalEvidenceReference(
        execution_id=item.source.execution_id,
        evidence_type=item.evidence_type,
        resource_id=item.resource_id,
        device_name=item.source.device_name,
        command=item.source.command,
        supporting_lines=item.supporting_lines[:4],
    )


def _matches_interface(item: DiagnosticEvidence, interface: str | None) -> bool:
    if interface is None:
        return True
    expected = _normalize_interface(interface)
    actual = item.attributes.get("interface")
    if isinstance(actual, str) and _normalize_interface(actual) == expected:
        return True
    resource_parts = item.resource_id.split("/", 2)
    resource_interface = resource_parts[2] if len(resource_parts) == 3 else ""
    return _normalize_interface(resource_interface) == expected


def _normalize_interface(value: str) -> str:
    normalized = normalize_resource_part(value)
    aliases = {
        "fa": "fastethernet",
        "gi": "gigabitethernet",
        "te": "tengigabitethernet",
        "lo": "loopback",
    }
    match = re.match(r"^([a-z]+)(.*)$", normalized)
    if not match:
        return normalized
    return f"{aliases.get(match.group(1), match.group(1))}{match.group(2)}"


def _evaluate_ospf_area_mismatch(
    cause: PredictedRootCause,
    evidence: list[DiagnosticEvidence],
    scope: CausalScope | None,
) -> CausalClaimDecision:
    """Chỉ so sánh OSPF area của đúng interface mục tiêu và topology peer."""

    if cause.interface is None:
        return _evaluate_device_ospf_area_mismatch(cause, evidence, scope)

    peer = _topology_peer(cause, scope)
    local = [
        item
        for item in evidence
        if item.evidence_type == EvidenceType.OSPF_CONFIG
        and normalize_resource_part(item.source.device_name)
        == normalize_resource_part(cause.device)
        and _matches_interface(item, cause.interface)
        and isinstance(item.attributes.get("area"), str)
    ]
    remote: list[DiagnosticEvidence] = []
    if peer is not None:
        remote = [
            item
            for item in evidence
            if item.evidence_type == EvidenceType.OSPF_CONFIG
            and normalize_resource_part(item.source.device_name)
            == normalize_resource_part(peer[0])
            and _matches_interface(item, peer[1])
            and isinstance(item.attributes.get("area"), str)
        ]
    if local and remote:
        local_area = str(local[0].attributes["area"])
        peer_area = str(remote[0].attributes["area"])
        if local_area != peer_area:
            return _decision(
                cause,
                [local[0], remote[0]],
                f"Hai đầu topology peer thuộc OSPF area khác nhau ({local_area} và {peer_area}).",
            )
        return _decision(
            cause,
            [],
            "Hai đầu topology peer đang thuộc cùng OSPF area.",
            missing_evidence=[],
        )

    # Một số lab không cung cấp topology peer đáng tin cậy. Với interface đã
    # được nêu rõ, area của chính interface là một outlier và adjacency bằng 0
    # trong khi các routed link còn lại cùng một area thì vẫn là evidence trực
    # tiếp đủ mạnh để xác nhận sai area cục bộ.
    if local:
        target_area = str(local[0].attributes["area"])
        other_areas = {
            str(item.attributes["area"])
            for item in evidence
            if item.evidence_type == EvidenceType.OSPF_CONFIG
            and normalize_resource_part(item.source.device_name)
            == normalize_resource_part(cause.device)
            and not _matches_interface(item, cause.interface)
            and isinstance(item.attributes.get("area"), str)
            and not _normalize_interface(
                str(item.attributes.get("interface", ""))
            ).startswith("loopback")
        }
        if (
            len(other_areas) == 1
            and target_area not in other_areas
            and local[0].attributes.get("adjacent_neighbor_count") == 0
        ):
            return _decision(
                cause,
                [local[0]],
                (
                    f"Interface mục tiêu ở area {target_area}, khác area "
                    f"{next(iter(other_areas))} của các routed link còn lại và "
                    "không có OSPF adjacency."
                ),
            )

    checks: list[CausalReadCheck] = []
    if not local and cause.interface is not None:
        checks.append(
            CausalReadCheck(
                device=cause.device,
                commands=[f"show ip ospf interface {cause.interface}"],
                reason="Thiếu OSPF area của interface mục tiêu.",
            )
        )
    if peer is not None and not remote:
        checks.append(
            CausalReadCheck(
                device=peer[0],
                commands=[f"show ip ospf interface {peer[1]}"],
                reason="Thiếu OSPF area của peer interface trong topology.",
            )
        )
    return _decision(
        cause,
        [],
        "Chưa đủ OSPF interface evidence của đúng hai đầu topology peer.",
        missing_evidence=[EvidenceType.OSPF_CONFIG],
        recommended_checks=checks,
    )


def _evaluate_device_ospf_area_mismatch(
    cause: PredictedRootCause,
    evidence: list[DiagnosticEvidence],
    scope: CausalScope | None,
) -> CausalClaimDecision:
    """Đối chiếu area trên từng topology link khi yêu cầu chỉ nêu thiết bị."""

    node_config_decision = _evaluate_node_ospf_area_statements(cause, evidence, scope)
    if node_config_decision is not None:
        return node_config_decision

    local_items = [
        item
        for item in evidence
        if item.evidence_type == EvidenceType.OSPF_CONFIG
        and normalize_resource_part(item.source.device_name)
        == normalize_resource_part(cause.device)
        and isinstance(item.attributes.get("area"), str)
        and isinstance(item.attributes.get("interface"), str)
        and not _normalize_interface(str(item.attributes["interface"])).startswith(
            "loopback"
        )
    ]
    checks: list[CausalReadCheck] = []
    compared: list[tuple[DiagnosticEvidence, DiagnosticEvidence]] = []
    for local in local_items:
        interface = str(local.attributes["interface"])
        scoped_cause = cause.model_copy(update={"interface": interface})
        peer = _topology_peer(scoped_cause, scope)
        if peer is None:
            continue
        remote = next(
            (
                item
                for item in evidence
                if item.evidence_type == EvidenceType.OSPF_CONFIG
                and normalize_resource_part(item.source.device_name)
                == normalize_resource_part(peer[0])
                and _matches_interface(item, peer[1])
                and isinstance(item.attributes.get("area"), str)
            ),
            None,
        )
        if remote is None:
            checks.append(
                CausalReadCheck(
                    device=peer[0],
                    commands=[f"show ip ospf interface {peer[1]}"],
                    reason=(
                        f"Thiếu OSPF area của peer nối với {cause.device} {interface}."
                    ),
                )
            )
            continue
        compared.append((local, remote))
        if str(local.attributes["area"]) != str(remote.attributes["area"]):
            return _decision(
                cause,
                [local, remote],
                (
                    f"Topology link {cause.device} {interface} có OSPF area "
                    f"{local.attributes['area']} khác peer {peer[0]} {peer[1]} "
                    f"area {remote.attributes['area']}."
                ),
            )

    if compared and not checks:
        return _decision(
            cause,
            [],
            "Các topology link đã đối chiếu đang dùng cùng OSPF area.",
            missing_evidence=[],
        )
    if not local_items:
        checks.append(
            CausalReadCheck(
                device=cause.device,
                commands=["show ip ospf interface"],
                reason="Thiếu OSPF area theo từng interface trên thiết bị mục tiêu.",
            )
        )
    return _decision(
        cause,
        [],
        "Chưa đủ OSPF area evidence để đối chiếu các topology link của thiết bị.",
        missing_evidence=[EvidenceType.OSPF_CONFIG],
        recommended_checks=checks[:4],
    )


def _evaluate_node_ospf_area_statements(
    cause: PredictedRootCause,
    evidence: list[DiagnosticEvidence],
    scope: CausalScope | None,
) -> CausalClaimDecision | None:
    """So sánh network statement của node với các topology peer đã thu thập."""

    local_configs = [
        item
        for item in evidence
        if item.evidence_type == EvidenceType.OSPF_CONFIG
        and normalize_resource_part(item.source.device_name)
        == normalize_resource_part(cause.device)
        and _ospf_statement_areas(item)
    ]
    if not local_configs or scope is None:
        return None
    peer_names = {
        normalize_resource_part(str(item.get("device", "")))
        for hostname, neighbors in scope.topology_neighbors.items()
        if normalize_resource_part(hostname) == normalize_resource_part(cause.device)
        for item in neighbors
        if item.get("device")
    }
    peer_configs = [
        item
        for item in evidence
        if item.evidence_type == EvidenceType.OSPF_CONFIG
        and normalize_resource_part(item.source.device_name) in peer_names
        and _ospf_statement_areas(item)
    ]
    local_areas = {
        area for item in local_configs for area in _ospf_statement_areas(item)
    }
    peer_areas = {area for item in peer_configs for area in _ospf_statement_areas(item)}
    if len(local_areas) == 1 and peer_areas and local_areas.isdisjoint(peer_areas):
        return _decision(
            cause,
            [local_configs[0], *peer_configs[:3]],
            (
                f"OSPF network statement của {cause.device} dùng area "
                f"{next(iter(local_areas))}, khác area "
                f"{', '.join(sorted(peer_areas))} trên các topology peer."
            ),
        )
    return None


def _ospf_statement_areas(item: DiagnosticEvidence) -> set[str]:
    """Lấy area từ các network statement đã được parser chuẩn hóa."""

    statements = item.attributes.get("network_statements", [])
    if not isinstance(statements, list):
        return set()
    return {
        match.group(1)
        for statement in statements
        if isinstance(statement, str)
        and (match := re.search(r"\barea\s+(\S+)", statement, re.IGNORECASE))
    }


def _topology_peer(
    cause: PredictedRootCause,
    scope: CausalScope | None,
) -> tuple[str, str] | None:
    if scope is None or cause.interface is None:
        return None
    neighbors = next(
        (
            items
            for hostname, items in scope.topology_neighbors.items()
            if normalize_resource_part(hostname)
            == normalize_resource_part(cause.device)
        ),
        [],
    )
    for item in neighbors:
        if _normalize_interface(
            item.get("local_interface", "")
        ) == _normalize_interface(cause.interface):
            device = item.get("device", "")
            interface = item.get("peer_interface", "")
            if device and interface and interface != "unknown":
                return device, interface
    return None


def _mismatched_ip_configuration(
    evidence: list[DiagnosticEvidence],
    fault: FaultType,
    cause: PredictedRootCause,
    scope: CausalScope | None,
) -> list[DiagnosticEvidence]:
    parsed: list[tuple[DiagnosticEvidence, ipaddress.IPv4Interface]] = []
    for item in evidence:
        address = item.attributes.get("ip_address")
        mask = item.attributes.get("subnet_mask")
        if not isinstance(address, str) or not isinstance(mask, str):
            continue
        try:
            parsed.append((item, ipaddress.IPv4Interface(f"{address}/{mask}")))
        except ValueError:
            continue
    for index, (left_item, left) in enumerate(parsed):
        for right_item, right in parsed[index + 1 :]:
            if left_item.source.device_name == right_item.source.device_name:
                continue
            pair = (left_item, right_item)
            if not _is_cause_peer_pair(pair, cause, scope):
                pair = (right_item, left_item)
                if not _is_cause_peer_pair(pair, cause, scope):
                    continue
            masks_differ = left.network.prefixlen != right.network.prefixlen
            networks_differ = left.network != right.network
            if fault == FaultType.WRONG_SUBNET_MASK and masks_differ:
                return [left_item, right_item]
            if (
                fault == FaultType.WRONG_IP_ADDRESS
                and not masks_differ
                and networks_differ
            ):
                return [left_item, right_item]
    return []


def _is_cause_peer_pair(
    pair: tuple[DiagnosticEvidence, DiagnosticEvidence],
    cause: PredictedRootCause,
    scope: CausalScope | None,
) -> bool:
    local, peer = pair
    if normalize_resource_part(local.source.device_name) != normalize_resource_part(
        cause.device
    ):
        return False
    if not _matches_interface(local, cause.interface):
        return False
    if scope is None or not scope.topology_neighbors or cause.interface is None:
        return True
    neighbors = next(
        (
            items
            for hostname, items in scope.topology_neighbors.items()
            if normalize_resource_part(hostname)
            == normalize_resource_part(cause.device)
        ),
        [],
    )
    return any(
        _normalize_interface(item.get("local_interface", ""))
        == _normalize_interface(cause.interface)
        and normalize_resource_part(item.get("device", ""))
        == normalize_resource_part(peer.source.device_name)
        and _matches_interface(peer, item.get("peer_interface"))
        for item in neighbors
    )
