"""Credential-bearing contract used only for device connections."""

from pydantic import BaseModel, Field


class DeviceConfig(BaseModel):
    """.Cấu hình kết nối thiết bị, bao gồm thông tin xác thực và các tham số kết nối."""
    gns3_node_name: str | None = None
    device_type: str = Field(description="Loại thiết bị, ví dụ: cisco_ios, cisco_nxos, juniper_junos, vios_l2, vios_l3, ...")
    hostname: str = Field(description="Địa chỉ IP hoặc hostname của thiết bị.")
    port: int = Field(gt=0, le=65535, description="Cổng kết nối của thiết bị.")
    username: str = Field(description="Username để kết nối thiết bị.")
    password: str = Field(description="Password để kết nối thiết bị.")
    secret: str = Field(default="", description="Secret để kết nối thiết bị.")

    def to_netmiko_params(self) -> dict[str, str | int]:
        """Map the contract to Netmiko keyword arguments."""
        data = self.model_dump()
        data.pop("gns3_node_name")
        data["host"] = data.pop("hostname")
        return data
