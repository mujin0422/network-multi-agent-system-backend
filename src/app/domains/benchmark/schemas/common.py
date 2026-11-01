"""Schema dùng chung trong Benchmark domain."""

from typing import Literal

from pydantic import BaseModel, Field


class BenchmarkAssertion(BaseModel):
    contains: str = Field(min_length=1)


class BenchmarkCheck(BaseModel):
    device: str = Field(min_length=1)
    command: str = Field(min_length=1)
    assertion: BenchmarkAssertion


class BenchmarkAction(BaseModel):
    device: str = Field(min_length=1)
    action: Literal["interface_shutdown", "interface_no_shutdown"]
    interface: str = Field(min_length=1)


class BenchmarkRootCause(BaseModel):
    fault_type: str = Field(min_length=1)
    device: str = Field(min_length=1)
    interface: str | None = None
