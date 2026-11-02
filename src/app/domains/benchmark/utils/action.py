"""Chuyển benchmark action có kiểu thành lệnh cấu hình thiết bị."""

from app.domains.benchmark.schemas import BenchmarkAction


def build_benchmark_action_commands(action: BenchmarkAction) -> list[str]:
    """Sinh danh sách lệnh WRITE đã giới hạn theo action, không nhận lệnh tùy ý."""

    if action.action in {"interface_shutdown", "interface_no_shutdown"}:
        command = "shutdown" if action.action == "interface_shutdown" else "no shutdown"
        return [f"interface {action.interface}", command]

    if action.action in {"mpls_enable", "mpls_disable"}:
        command = "mpls ip" if action.action == "mpls_enable" else "no mpls ip"
        return [f"interface {action.interface}", command]

    if action.action in {"ospf_network_add", "ospf_network_remove"}:
        prefix = "" if action.action == "ospf_network_add" else "no "
        return [
            f"router ospf {action.process_id}",
            f"{prefix}network {action.network} {action.wildcard} area {action.area}",
        ]

    if action.action in {"default_route_add", "default_route_remove"}:
        prefix = "" if action.action == "default_route_add" else "no "
        return [f"{prefix}ip route 0.0.0.0 0.0.0.0 {action.next_hop}"]

    if action.action == "interface_ip_set":
        return [
            f"interface {action.interface}",
            f"ip address {action.ip_address} {action.subnet_mask}",
        ]

    if action.action == "acl_block":
        return [
            f"access-list {action.acl_number} deny ip {action.source_network} "
            f"{action.source_wildcard} any",
            f"access-list {action.acl_number} permit ip any any",
            f"interface {action.interface}",
            f"ip access-group {action.acl_number} {action.direction}",
        ]

    return [
        f"interface {action.interface}",
        f"no ip access-group {action.acl_number} {action.direction}",
        f"no access-list {action.acl_number}",
    ]
