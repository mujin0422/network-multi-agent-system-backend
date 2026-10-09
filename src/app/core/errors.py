"""Các lỗi nghiệp vụ dùng chung giữa các domain."""


class DomainError(Exception):
    """Lớp cơ sở cho lỗi có thể chuyển thành HTTP response an toàn."""


class ResourceNotFoundError(DomainError):
    """Tài nguyên nghiệp vụ không tồn tại."""


class ResourceConflictError(DomainError):
    """Dữ liệu vi phạm quy tắc duy nhất hoặc xung đột trạng thái."""


class InvalidStateTransitionError(DomainError):
    """Yêu cầu chuyển trạng thái không hợp lệ theo state machine."""
