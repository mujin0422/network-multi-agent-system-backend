"""Dependency composition cho System Audit HTTP routes."""

from functools import lru_cache

from app.core.config import get_settings
from app.domains.audit.repositories import AuditLogRepository
from app.domains.audit.services import AuditLogService


@lru_cache
def _build_audit_log_service() -> AuditLogService:
    """Khởi tạo service dùng chung từ database URL của ứng dụng."""

    return AuditLogService(AuditLogRepository(get_settings().database_url))


async def get_audit_log_service() -> AuditLogService:
    """Cung cấp AuditLogService cho FastAPI dependency injection."""

    return _build_audit_log_service()
