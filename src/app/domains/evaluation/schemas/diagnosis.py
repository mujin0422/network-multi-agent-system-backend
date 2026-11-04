"""Neutral schema for machine-readable root-cause claims from any AI agent."""

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class FaultType(StrEnum):
    """Taxonomy RCA chuẩn dùng chung cho Analyst, ground truth và evaluator."""

    LINK_DOWN = "link_down"
    OSPF_NETWORK_MISSING = "ospf_network_missing"
    OSPF_AREA_MISMATCH = "ospf_area_mismatch"
    MPLS_DISABLED = "mpls_disabled"
    DEFAULT_ROUTE_MISSING = "default_route_missing"
    WRONG_SUBNET_MASK = "wrong_subnet_mask"
    WRONG_IP_ADDRESS = "wrong_ip_address"
    ACL_TRAFFIC_BLOCK = "acl_traffic_block"
    LOOPBACK_ADMIN_DOWN = "loopback_admin_down"
    BGP_NEIGHBOR_ADMIN_DOWN = "bgp_neighbor_admin_down"


_FAULT_TYPE_ALIASES = {
    "acl_block": FaultType.ACL_TRAFFIC_BLOCK,
    "access_list_block": FaultType.ACL_TRAFFIC_BLOCK,
    "wrong_netmask": FaultType.WRONG_SUBNET_MASK,
    "subnet_mask_mismatch": FaultType.WRONG_SUBNET_MASK,
    "incorrect_ip_address": FaultType.WRONG_IP_ADDRESS,
    "ospf_missing_network": FaultType.OSPF_NETWORK_MISSING,
    "mpls_ip_disabled": FaultType.MPLS_DISABLED,
    "bgp_neighbor_shutdown": FaultType.BGP_NEIGHBOR_ADMIN_DOWN,
}

NODE_SCOPED_FAULT_TYPES = frozenset(
    {
        FaultType.OSPF_NETWORK_MISSING,
        FaultType.DEFAULT_ROUTE_MISSING,
        FaultType.BGP_NEIGHBOR_ADMIN_DOWN,
    }
)
INTERFACE_SCOPED_FAULT_TYPES = frozenset(
    {
        FaultType.LINK_DOWN,
        FaultType.MPLS_DISABLED,
        FaultType.WRONG_SUBNET_MASK,
        FaultType.WRONG_IP_ADDRESS,
        FaultType.ACL_TRAFFIC_BLOCK,
        FaultType.LOOPBACK_ADMIN_DOWN,
    }
)


def canonical_fault_type(value: object) -> FaultType:
    """Chuẩn hóa alias và cách viết thành một mã fault duy nhất."""

    if isinstance(value, FaultType):
        return value
    normalized = str(value).strip().casefold().replace("-", "_").replace(" ", "_")
    alias = _FAULT_TYPE_ALIASES.get(normalized)
    return alias if alias is not None else FaultType(normalized)


class PredictedRootCause(BaseModel):
    """A proposed fault source; benchmark ground truth is never loaded here."""

    device: str = Field(min_length=1, max_length=100)
    interface: str | None = Field(default=None, max_length=100)
    fault_type: FaultType

    @field_validator("fault_type", mode="before")
    @classmethod
    def normalize_fault_type(cls, value: object) -> FaultType:
        """Không cho Analyst tạo mã tùy ý ngoài taxonomy chuẩn."""

        return canonical_fault_type(value)

    @model_validator(mode="after")
    def normalize_resource_scope(self) -> "PredictedRootCause":
        """Chuẩn hóa node/interface theo phạm vi tự nhiên của từng fault."""

        if self.fault_type in NODE_SCOPED_FAULT_TYPES:
            self.interface = None
        return self
