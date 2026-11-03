"""Schema dùng chung trong Benchmark domain."""

from ipaddress import IPv4Address
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class BenchmarkAssertion(BaseModel):
    contains: str | None = Field(default=None, min_length=1)
    not_contains: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_one_condition(self) -> "BenchmarkAssertion":
        """Mỗi check phải xác nhận nội dung xuất hiện hoặc không xuất hiện."""

        if (self.contains is None) == (self.not_contains is None):
            raise ValueError("Assertion phải có đúng một contains hoặc not_contains")
        return self


class BenchmarkCheck(BaseModel):
    device: str = Field(min_length=1)
    command: str = Field(min_length=1)
    assertion: BenchmarkAssertion


class BenchmarkAction(BaseModel):
    device: str = Field(min_length=1)
    action: Literal[
        "interface_shutdown",
        "interface_no_shutdown",
        "ospf_network_add",
        "ospf_network_remove",
        "mpls_enable",
        "mpls_disable",
        "default_route_add",
        "default_route_remove",
        "interface_ip_set",
        "acl_block",
        "acl_remove",
        "bgp_neighbor_shutdown",
        "bgp_neighbor_no_shutdown",
    ]
    interface: str | None = None
    process_id: int | None = Field(default=None, ge=1, le=65535)
    network: str | None = None
    wildcard: str | None = None
    area: int | None = Field(default=None, ge=0)
    next_hop: str | None = None
    ip_address: str | None = None
    subnet_mask: str | None = None
    acl_number: int | None = Field(default=None, ge=1, le=199)
    direction: Literal["in", "out"] | None = None
    source_network: str | None = None
    source_wildcard: str | None = None
    local_as: int | None = Field(default=None, ge=1, le=4294967295)
    neighbor_ip: str | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> "BenchmarkAction":
        """Bắt buộc đúng tham số theo từng loại fault injection được hỗ trợ."""

        requirements = {
            "interface_shutdown": ("interface",),
            "interface_no_shutdown": ("interface",),
            "ospf_network_add": ("process_id", "network", "wildcard", "area"),
            "ospf_network_remove": ("process_id", "network", "wildcard", "area"),
            "mpls_enable": ("interface",),
            "mpls_disable": ("interface",),
            "default_route_add": ("next_hop",),
            "default_route_remove": ("next_hop",),
            "interface_ip_set": ("interface", "ip_address", "subnet_mask"),
            "acl_block": (
                "interface", "acl_number", "direction",
                "source_network", "source_wildcard",
            ),
            "acl_remove": ("interface", "acl_number", "direction"),
            "bgp_neighbor_shutdown": ("local_as", "neighbor_ip"),
            "bgp_neighbor_no_shutdown": ("local_as", "neighbor_ip"),
        }
        missing = [
            field_name
            for field_name in requirements[self.action]
            if getattr(self, field_name) is None
        ]
        if missing:
            raise ValueError(
                f"Action '{self.action}' thiếu tham số: {', '.join(missing)}"
            )

        # A strict IPv4 address prevents arbitrary CLI fragments in a BGP neighbor.
        if self.action in {"bgp_neighbor_shutdown", "bgp_neighbor_no_shutdown"}:
            try:
                IPv4Address(self.neighbor_ip)
            except ValueError as error:
                raise ValueError("BGP neighbor_ip phải là địa chỉ IPv4 hợp lệ") from error
        return self


class BenchmarkRootCause(BaseModel):
    fault_type: str = Field(min_length=1)
    device: str = Field(min_length=1)
    interface: str | None = None
