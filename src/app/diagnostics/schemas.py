"""Contract dùng chung cho playbook và evidence chẩn đoán."""

from datetime import UTC, datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field
from app.domains.evaluation.schemas import FaultType

JsonScalar = str | bool | int | float | None


class PlaybookTarget(StrEnum):
    PRIMARY = "PRIMARY"
    NEIGHBOR = "NEIGHBOR"


class EvidenceType(StrEnum):
    INTERFACE_STATUS = "INTERFACE_STATUS"
    INTERFACE_CONFIG = "INTERFACE_CONFIG"
    IP_CONFIGURATION = "IP_CONFIGURATION"
    ROUTE = "ROUTE"
    OSPF_NEIGHBOR = "OSPF_NEIGHBOR"
    OSPF_CONFIG = "OSPF_CONFIG"
    MPLS_INTERFACE = "MPLS_INTERFACE"
    LDP_NEIGHBOR = "LDP_NEIGHBOR"
    BGP_NEIGHBOR = "BGP_NEIGHBOR"
    BGP_CONFIG = "BGP_CONFIG"
    ACL = "ACL"
    UNKNOWN = "UNKNOWN"


class DiagnosticCommand(BaseModel):
    model_config = ConfigDict(frozen=True)
    command_template: str = Field(min_length=1)
    parser: str = Field(min_length=1)
    target: PlaybookTarget = PlaybookTarget.PRIMARY
    required: bool = True
    produces: tuple[EvidenceType, ...] = Field(min_length=1)


class DiagnosticPlaybook(BaseModel):
    model_config = ConfigDict(frozen=True)
    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    fault_types: tuple[FaultType, ...] = Field(min_length=1)
    keywords: tuple[str, ...] = Field(min_length=1)
    supported_device_types: tuple[str, ...] = ("cisco_ios", "cisco_ios_telnet")
    commands: tuple[DiagnosticCommand, ...] = Field(min_length=1)
    required_evidence: tuple[EvidenceType, ...] = Field(min_length=1)

    def planner_payload(self) -> dict:
        """Rút gọn playbook thành dữ liệu an toàn cho Planner prompt."""
        return {
            "key": self.key,
            "fault_types": [item.value for item in self.fault_types],
            "commands": [
                {
                    "command_template": item.command_template,
                    "target": item.target.value,
                    "required": item.required,
                }
                for item in self.commands
            ],
            "required_evidence": [item.value for item in self.required_evidence],
        }


class EvidenceSource(BaseModel):
    execution_id: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    device_name: str = Field(min_length=1)
    command: str = Field(min_length=1)
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DiagnosticEvidence(BaseModel):
    evidence_type: EvidenceType
    resource_id: str = Field(min_length=1)
    source: EvidenceSource
    attributes: dict[str, JsonScalar | list[JsonScalar]] = Field(default_factory=dict)
    supporting_lines: list[str] = Field(default_factory=list)
    raw_output: str


class EvidenceCoverage(BaseModel):
    """Mức độ đáp ứng required evidence của các playbook đang áp dụng."""

    applicable: bool
    playbook_keys: list[str] = Field(default_factory=list)
    required: list[EvidenceType] = Field(default_factory=list)
    observed: list[EvidenceType] = Field(default_factory=list)
    missing: list[EvidenceType] = Field(default_factory=list)
    coverage: float = Field(ge=0.0, le=1.0)

    @property
    def complete(self) -> bool:
        return not self.applicable or not self.missing
