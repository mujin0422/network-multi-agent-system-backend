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
    """Chọn playbook theo dấu hiệu; triệu chứng OSPF chung phải xét nhiều giả thuyết."""
    normalized = user_message.casefold()
    selected = [
        item
        for item in ALL_PLAYBOOKS
        if any(key.casefold() in normalized for key in item.keywords)
    ]

    # Yêu cầu thực tế thường chỉ mô tả "adjacency/neighbor không hình thành",
    # chưa thể biết trước là thiếu network statement hay lệch area. Giữ cả hai
    # playbook để evidence gate phân biệt thay vì khóa sớm vào một nguyên nhân.
    generic_ospf_symptoms = (
        "ospf adjacency",
        "ospf neighbor",
        "neighbor ospf",
        "láng giềng ospf",
    )
    if any(symptom in normalized for symptom in generic_ospf_symptoms):
        for key in ("ospf_network_missing", "ospf_area_mismatch"):
            playbook = _BY_KEY[key]
            if playbook not in selected:
                selected.append(playbook)
    return tuple(selected)
