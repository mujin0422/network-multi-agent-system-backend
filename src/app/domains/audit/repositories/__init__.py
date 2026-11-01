"""Public repositories của System Audit domain."""

from app.domains.audit.repositories.audit_log import (
    AuditLogRepository,
    AuditLogRepositoryProtocol,
)

__all__ = ["AuditLogRepository", "AuditLogRepositoryProtocol"]
