"""Catalog các playbook chẩn đoán được hỗ trợ."""

from app.diagnostics.schemas import DiagnosticCommand as Command
from app.diagnostics.schemas import DiagnosticPlaybook as Playbook
from app.diagnostics.schemas import EvidenceType as Evidence
from app.diagnostics.schemas import PlaybookTarget as Target
from app.domains.evaluation.schemas import FaultType

INTERFACE_LINK_DOWN = Playbook(
    key="interface_link_down",
    name="Interface link-down",
    fault_types=(FaultType.LINK_DOWN, FaultType.LOOPBACK_ADMIN_DOWN),
    keywords=(
        "link down",
        "link-down",
        "interface down",
        "cổng bị tắt",
        "shutdown",
        "đường kết nối",
        "bị gián đoạn",
        "loopback",
    ),
    commands=(
        Command(
            command_template="show interfaces {interface}",
            parser="interface",
            produces=(Evidence.INTERFACE_STATUS,),
        ),
        Command(
            command_template="show running-config interface {interface}",
            parser="interface",
            produces=(Evidence.INTERFACE_CONFIG, Evidence.IP_CONFIGURATION),
        ),
        Command(
            command_template="show interfaces {peer_interface}",
            parser="interface",
            target=Target.NEIGHBOR,
            produces=(Evidence.INTERFACE_STATUS,),
        ),
    ),
    required_evidence=(Evidence.INTERFACE_STATUS, Evidence.INTERFACE_CONFIG),
)

IP_COMMANDS = (
    Command(
        command_template="show ip interface brief",
        parser="interface",
        produces=(Evidence.INTERFACE_STATUS, Evidence.IP_CONFIGURATION),
    ),
    Command(
        command_template="show running-config interface {interface}",
        parser="interface",
        produces=(Evidence.INTERFACE_CONFIG, Evidence.IP_CONFIGURATION),
    ),
    Command(
        command_template="show running-config interface {peer_interface}",
        parser="interface",
        target=Target.NEIGHBOR,
        produces=(Evidence.INTERFACE_CONFIG, Evidence.IP_CONFIGURATION),
    ),
    Command(
        command_template="show ip route connected",
        parser="route",
        produces=(Evidence.ROUTE,),
    ),
)
WRONG_IP_ADDRESS = Playbook(
    key="wrong_ip_address",
    name="Wrong interface IP address",
    fault_types=(FaultType.WRONG_IP_ADDRESS,),
    keywords=(
        "wrong ip",
        "sai địa chỉ ip",
        "incorrect ip",
        "ip mismatch",
        "trao đổi lưu lượng đúng",
    ),
    commands=IP_COMMANDS,
    required_evidence=(Evidence.IP_CONFIGURATION, Evidence.ROUTE),
)
WRONG_SUBNET_MASK = Playbook(
    key="wrong_subnet_mask",
    name="Wrong subnet mask",
    fault_types=(FaultType.WRONG_SUBNET_MASK,),
    keywords=("subnet mask", "netmask", "sai mask", "bad mask", "mask mismatch"),
    commands=IP_COMMANDS,
    required_evidence=(Evidence.IP_CONFIGURATION, Evidence.ROUTE),
)

OSPF_COMMANDS = (
    Command(
        command_template="show ip ospf neighbor",
        parser="ospf",
        produces=(Evidence.OSPF_NEIGHBOR,),
    ),
    Command(
        command_template="show ip ospf interface {interface}",
        parser="ospf",
        produces=(Evidence.OSPF_CONFIG,),
    ),
    Command(
        command_template="show running-config | section router ospf",
        parser="ospf",
        produces=(Evidence.OSPF_CONFIG,),
    ),
    Command(
        command_template="show ip ospf interface {peer_interface}",
        parser="ospf",
        target=Target.NEIGHBOR,
        produces=(Evidence.OSPF_CONFIG,),
    ),
)
OSPF_NETWORK_MISSING = Playbook(
    key="ospf_network_missing",
    name="Missing OSPF network statement",
    fault_types=(FaultType.OSPF_NETWORK_MISSING,),
    keywords=(
        "ospf network",
        "missing ospf",
        "thiếu ospf",
        "không có ospf",
        "ospf adjacency",
        "tham gia ospf",
    ),
    commands=OSPF_COMMANDS,
    required_evidence=(Evidence.OSPF_CONFIG, Evidence.OSPF_NEIGHBOR),
)
OSPF_AREA_MISMATCH = Playbook(
    key="ospf_area_mismatch",
    name="OSPF area mismatch",
    fault_types=(FaultType.OSPF_AREA_MISMATCH,),
    keywords=("area mismatch", "sai area", "ospf area", "mismatch ospf"),
    commands=OSPF_COMMANDS,
    required_evidence=(Evidence.OSPF_CONFIG, Evidence.OSPF_NEIGHBOR),
)

MPLS_DISABLED = Playbook(
    key="mpls_disabled",
    name="MPLS disabled on interface",
    fault_types=(FaultType.MPLS_DISABLED,),
    keywords=("mpls", "ldp", "label distribution"),
    commands=(
        Command(
            command_template="show mpls interfaces",
            parser="mpls",
            produces=(Evidence.MPLS_INTERFACE,),
        ),
        Command(
            command_template="show mpls ldp neighbor",
            parser="mpls",
            produces=(Evidence.LDP_NEIGHBOR,),
        ),
        Command(
            command_template="show running-config interface {interface}",
            parser="interface",
            produces=(Evidence.INTERFACE_CONFIG,),
        ),
        Command(
            command_template="show mpls interfaces",
            parser="mpls",
            target=Target.NEIGHBOR,
            produces=(Evidence.MPLS_INTERFACE,),
        ),
    ),
    required_evidence=(Evidence.MPLS_INTERFACE, Evidence.LDP_NEIGHBOR),
)
BGP_NEIGHBOR_DOWN = Playbook(
    key="bgp_neighbor_admin_down",
    name="BGP neighbor administratively down",
    fault_types=(FaultType.BGP_NEIGHBOR_ADMIN_DOWN,),
    keywords=("bgp", "ebgp", "ibgp", "neighbor shutdown", "peer down"),
    commands=(
        Command(
            command_template="show ip bgp summary",
            parser="bgp",
            produces=(Evidence.BGP_NEIGHBOR,),
        ),
        Command(
            command_template="show running-config | section router bgp",
            parser="bgp",
            produces=(Evidence.BGP_CONFIG,),
        ),
        Command(
            command_template="show ip bgp summary",
            parser="bgp",
            target=Target.NEIGHBOR,
            produces=(Evidence.BGP_NEIGHBOR,),
        ),
    ),
    required_evidence=(Evidence.BGP_NEIGHBOR, Evidence.BGP_CONFIG),
)
ACL_TRAFFIC_BLOCK = Playbook(
    key="acl_traffic_block",
    name="ACL blocks expected traffic",
    fault_types=(FaultType.ACL_TRAFFIC_BLOCK,),
    keywords=(
        "acl",
        "access-list",
        "access list",
        "chặn kết nối",
        "traffic block",
        "bị chặn",
    ),
    commands=(
        Command(
            command_template="show access-lists", parser="acl", produces=(Evidence.ACL,)
        ),
        Command(
            command_template="show running-config interface {interface}",
            parser="interface",
            produces=(Evidence.INTERFACE_CONFIG, Evidence.ACL),
        ),
    ),
    required_evidence=(Evidence.ACL, Evidence.INTERFACE_CONFIG),
)
DEFAULT_ROUTE_MISSING = Playbook(
    key="default_route_missing",
    name="Missing default route",
    fault_types=(FaultType.DEFAULT_ROUTE_MISSING,),
    keywords=("default route", "gateway of last resort", "route mặc định", "0.0.0.0/0"),
    commands=(
        Command(
            command_template="show ip route 0.0.0.0",
            parser="route",
            produces=(Evidence.ROUTE,),
        ),
        Command(
            command_template="show running-config | include ^ip route 0.0.0.0",
            parser="route",
            produces=(Evidence.ROUTE,),
        ),
    ),
    required_evidence=(Evidence.ROUTE,),
)

ALL_PLAYBOOKS = (
    INTERFACE_LINK_DOWN,
    WRONG_IP_ADDRESS,
    WRONG_SUBNET_MASK,
    OSPF_NETWORK_MISSING,
    OSPF_AREA_MISMATCH,
    MPLS_DISABLED,
    BGP_NEIGHBOR_DOWN,
    ACL_TRAFFIC_BLOCK,
    DEFAULT_ROUTE_MISSING,
)
