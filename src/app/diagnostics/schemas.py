"""Contract dùng chung cho playbook và evidence chẩn đoán."""

from datetime import UTC, datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field
from app.domains.evaluation.schemas import FaultType

JsonScalar = str | bool | int | float | None
JsonValue = JsonScalar | list[JsonScalar] | list[dict[str, JsonScalar]]


class PlaybookTarget(StrEnum):
    """Mục tiêu của command chẩn đoán trong playbook."""
    PRIMARY = "PRIMARY"
    NEIGHBOR = "NEIGHBOR"


class EvidenceType(StrEnum):
    """Các loại bằng chứng chẩn đoán mà Analyst Agent có thể thu thập."""
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
    """Một command chẩn đoán, bao gồm template, parser, target và các metadata liên quan."""
    model_config = ConfigDict(frozen=True)

    command_template: str = Field(min_length=1, description="Template của command chẩn đoán.")
    parser: str = Field(min_length=1, description="Parser dùng để phân tích output của command.")
    target: PlaybookTarget = Field(default=PlaybookTarget.PRIMARY, description="Mục tiêu của command.")
    required: bool = Field(default=True, description="Cho biết command có bắt buộc phải thực thi không.")
    produces: tuple[EvidenceType, ...] = Field(min_length=1, description="Danh sách các EvidenceType mà command này tạo ra.")


class DiagnosticPlaybook(BaseModel):
    """Một playbook chẩn đoán, bao gồm các command, evidence cần thiết và các metadata liên quan."""
    model_config = ConfigDict(frozen=True)

    key: str = Field(min_length=1, description="Khóa duy nhất của playbook, dùng để tham chiếu trong các evidence.")
    name: str = Field(min_length=1, description="Tên của playbook.")
    fault_types: tuple[FaultType, ...] = Field(min_length=1, description="Danh sách các FaultType mà playbook này áp dụng.")
    keywords: tuple[str, ...] = Field(min_length=1, description="Các từ khóa liên quan đến playbook.")
    supported_device_types: tuple[str, ...] = Field(default=("cisco_ios", "cisco_ios_telnet"), description="Các loại thiết bị được hỗ trợ bởi playbook.")
    commands: tuple[DiagnosticCommand, ...] = Field(min_length=1, description="Danh sách các command được thực thi trong playbook.")
    required_evidence: tuple[EvidenceType, ...] = Field(min_length=1, description="Danh sách các evidence cần thiết để thực hiện playbook.")

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
    """Thông tin nguồn gốc của evidence."""
    execution_id: str = Field(min_length=1, description="ID của execution mà evidence này được thu thập.")
    device_id: str = Field(min_length=1, description="ID của thiết bị mà evidence này được thu thập.")
    device_name: str = Field(min_length=1, description="Tên của thiết bị mà evidence này được thu thập.")
    command: str = Field(min_length=1, description="Command đã được thực thi để thu thập evidence.")
    collected_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="Thời gian evidence được thu thập.")


class DiagnosticEvidence(BaseModel):
    """Một bằng chứng chẩn đoán được thu thập từ thiết bị mạng."""
    evidence_type: EvidenceType
    resource_id: str = Field(min_length=1, description="ID của resource mà evidence này liên quan, ví dụ interface ID hoặc route ID.")
    source: EvidenceSource = Field(description="Thông tin nguồn gốc của evidence.")
    attributes: dict[str, JsonValue] = Field(default_factory=dict, description="Các thuộc tính bổ sung cho evidence.")
    supporting_lines: list[str] = Field(default_factory=list, description="Các dòng output hỗ trợ cho evidence.")
    raw_output: str = Field(default="", description="Raw output của command, có thể dùng để debug hoặc phân tích thêm.")


class EvidenceCoverage(BaseModel):
    """Mức độ đáp ứng required evidence của các playbook đang áp dụng."""
    applicable: bool = Field(default=False, description="True nếu có playbook đang áp dụng, False nếu không.")
    playbook_keys: list[str] = Field(default_factory=list, description="Danh sách các playbook đang áp dụng.")
    required: list[EvidenceType] = Field(default_factory=list, description="Danh sách các EvidenceType được yêu cầu bởi các playbook đang áp dụng.")
    observed: list[EvidenceType] = Field(default_factory=list, description="Danh sách các EvidenceType đã thu thập được.")
    missing: list[EvidenceType] = Field(default_factory=list, description="Danh sách các EvidenceType được yêu cầu nhưng chưa thu thập được.")
    coverage: float = Field(ge=0.0, le=1.0, description="Tỷ lệ coverage của evidence.")

    @property
    def complete(self) -> bool:
        return not self.applicable or not self.missing
