"""Contracts owned by the network domain."""

from pydantic import BaseModel, Field


class DeviceConfig(BaseModel):
    device_type: str
    hostname: str
    port: int = Field(gt=0, le=65535)
    username: str
    password: str
    secret: str = ""

    def to_netmiko_params(self) -> dict[str, str | int]:
        """Map this contract to the keyword arguments expected by Netmiko."""
        data = self.model_dump()
        data["host"] = data.pop("hostname")
        return data


class NetworkStatus(BaseModel):
    status: str
