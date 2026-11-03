"""Request, response và record schema của benchmark_scenarios."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domains.benchmark.schemas.common import (
    BenchmarkAction,
    BenchmarkCheck,
    BenchmarkRootCause,
)


class BenchmarkScenario(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    scenario_key: str = Field(
        max_length=100,
        pattern=r"^[a-z0-9][a-z0-9-]*$",
    )
    version: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    topology: str = Field(min_length=1, max_length=100)
    initial_message: str = Field(min_length=1)
    preconditions: list[BenchmarkCheck] = Field(default_factory=list)
    injection: list[BenchmarkAction] = Field(min_length=1)
    fault_verification: list[BenchmarkCheck] = Field(min_length=1)
    ground_truth: list[BenchmarkRootCause] = Field(min_length=1)
    evaluation_required_terms: list[str] = Field(min_length=1)
    cleanup: list[BenchmarkAction] = Field(min_length=1)


class BenchmarkScenarioSummary(BaseModel):
    id: str = Field(pattern=r"^benc-\d{6}-[0-9a-f]{8}$")
    scenario_key: str
    version: str
    name: str
    description: str
    topology: str
    initial_message: str
    is_active: bool = True
    created_at: datetime | None = None
    last_updated_at: datetime | None = None


class BenchmarkScenarioRecord(BenchmarkScenario):
    id: str = Field(pattern=r"^benc-\d{6}-[0-9a-f]{8}$")
    is_active: bool = True
    created_by: str | None = None
    last_updated_by: str | None = None
    created_at: datetime
    last_updated_at: datetime

    @model_validator(mode="before")
    @classmethod
    def merge_definition(cls, value: object) -> object:
        """Trải definition JSONB của ORM thành các trường scenario."""

        if isinstance(value, dict) or not hasattr(value, "definition"):
            return value
        return {
            "id": value.id,
            "scenario_key": value.scenario_key,
            "version": value.version,
            "name": value.name,
            "description": value.description,
            "topology": value.topology,
            "initial_message": value.initial_message,
            **value.definition,
            "is_active": value.is_active,
            "created_by": value.created_by,
            "last_updated_by": value.last_updated_by,
            "created_at": value.created_at,
            "last_updated_at": value.last_updated_at,
        }


class BenchmarkScenarioUpdate(BaseModel):
    version: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=500)
    topology: str | None = Field(default=None, min_length=1, max_length=100)
    initial_message: str | None = Field(default=None, min_length=1)
    preconditions: list[BenchmarkCheck] | None = None
    injection: list[BenchmarkAction] | None = Field(default=None, min_length=1)
    fault_verification: list[BenchmarkCheck] | None = Field(default=None, min_length=1)
    ground_truth: list[BenchmarkRootCause] | None = Field(default=None, min_length=1)
    evaluation_required_terms: list[str] | None = Field(default=None, min_length=1)
    cleanup: list[BenchmarkAction] | None = Field(default=None, min_length=1)
    is_active: bool | None = None
