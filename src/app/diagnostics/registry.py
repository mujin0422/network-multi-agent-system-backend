"""Registry bất biến cho việc tra cứu và chọn playbook."""

from app.diagnostics.playbooks import ALL_PLAYBOOKS
from app.diagnostics.schemas import DiagnosticPlaybook
from app.domains.evaluation.schemas import FaultType
from app.domains.evaluation.schemas.diagnosis import canonical_fault_type

_BY_KEY = {item.key: item for item in ALL_PLAYBOOKS}
_BY_FAULT = {fault: item for item in ALL_PLAYBOOKS for fault in item.fault_types}


def list_playbooks() -> tuple[DiagnosticPlaybook, ...]:
    """Lấy toàn bộ playbook theo thứ tự ổn định."""
    return ALL_PLAYBOOKS


def get_playbook(value: str | FaultType) -> DiagnosticPlaybook | None:
    """Lấy playbook theo key hoặc fault type chuẩn."""
    if isinstance(value, str) and value in _BY_KEY:
        return _BY_KEY[value]
    try:
        return _BY_FAULT.get(canonical_fault_type(value))
    except ValueError:
        return None


def select_playbooks(user_message: str) -> tuple[DiagnosticPlaybook, ...]:
    """Chọn playbook bằng keyword, không tự tạo loại sự cố mới."""
    normalized = user_message.casefold()
    return tuple(
        item
        for item in ALL_PLAYBOOKS
        if any(key.casefold() in normalized for key in item.keywords)
    )
