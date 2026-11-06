"""Tính độ phủ evidence theo playbook mà không phụ thuộc LangGraph."""

from app.diagnostics.registry import get_playbook
from app.diagnostics.schemas import DiagnosticEvidence, EvidenceCoverage, EvidenceType


def evaluate_evidence_coverage(
    playbook_keys: list[str],
    evidence: list[DiagnosticEvidence],
) -> EvidenceCoverage:
    """So sánh tập EvidenceType quan sát được với yêu cầu của playbook."""

    playbooks = [playbook for key in playbook_keys if (playbook := get_playbook(key))]
    required = {item for playbook in playbooks for item in playbook.required_evidence}
    observed = {
        item.evidence_type
        for item in evidence
        if item.evidence_type != EvidenceType.UNKNOWN
    }
    matched = required & observed
    return EvidenceCoverage(
        applicable=bool(playbooks),
        playbook_keys=[playbook.key for playbook in playbooks],
        required=sorted(required, key=str),
        observed=sorted(observed, key=str),
        missing=sorted(required - observed, key=str),
        coverage=len(matched) / len(required) if required else 1.0,
    )
