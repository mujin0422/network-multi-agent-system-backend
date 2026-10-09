"""Input and output contracts for the agent application layer."""

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    response: str
    agent: str


class AgentListResponse(BaseModel):
    agents: list[str]
