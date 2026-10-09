from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langgraph.graph import MessagesState

class DeviceConnection(BaseModel): 
    hostname: str = Field(default="")
    device_type: str = Field(default="cisco_ios")
    username: str = Field(default="")
    password: str = Field(default="")
    port: int = Field(default=22)

    class Config:
        arbitrary_types_allowed = True
        populate_by_name = True
        extra = "ignore"


class ToolRawData(BaseModel):
    tool_name: str = Field(default="")
    raw_data: str = Field(default="")


class InputNetworkExpert(BaseModel):
    human_mesage: str = Field(default="")


class OuputNetworkExpert(BaseModel):
    tools_used: List[str] = Field(default_factory=list)
    raw_data: Dict[str, str] = Field(default_factory=dict)
    tool_results: List[ToolRawData] = Field(default_factory=list)


class InputAnalysts(BaseModel):
    tools_used: List[str] = Field(default_factory=list)
    raw_data: Dict[str, str] = Field(default_factory=dict)
    human_mesage: str = Field(default="")


class OuputAnalysts(BaseModel):
    final_report: str = Field(default="")
    status: str = Field(default="completed")

    @classmethod
    def fromMessages(cls, messages: list) -> "OuputAnalysts":
        final_report = ""

        if messages:
            last_message = messages[-1]
            final_report = getattr(last_message, "content", "") or ""

        return cls(
            final_report=final_report,
            status="completed",
        )


class NetworkState(MessagesState):
    # Dữ liệu vào/ra có cấu trúc giữa các agent
    input_network_expert: Optional[InputNetworkExpert] = Field(default=None)
    output_network_expert: Optional[OuputNetworkExpert] = Field(default=None)
    input_analysts: Optional[InputAnalysts] = Field(default=None)
    output_analysts: Optional[OuputAnalysts] = Field(default=None)
