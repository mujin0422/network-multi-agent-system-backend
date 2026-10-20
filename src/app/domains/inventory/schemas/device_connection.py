"""Credential-bearing contract used only for device connections."""

from pydantic import BaseModel, Field


class DeviceConfig(BaseModel):
    gns3_node_name: str | None = None
    device_type: str
    hostname: str
    port: int = Field(gt=0, le=65535)
    username: str
    password: str
    secret: str = ""

    def to_netmiko_params(self) -> dict[str, str | int]:
        """Map the contract to Netmiko keyword arguments."""
        data = self.model_dump()
        data.pop("gns3_node_name")
        data["host"] = data.pop("hostname")
        return data
