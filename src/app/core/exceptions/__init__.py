"""Public exports for shared domain exceptions."""

from app.core.exceptions.domain import (
    AuthenticationError,
    AuthorizationError,
    DomainError,
    ExternalServiceUnavailableError,
    InvalidStateTransitionError,
    ResourceConflictError,
    ResourceNotFoundError,
)

__all__ = [
    "AuthenticationError",
    "AuthorizationError",
    "DomainError",
    "ExternalServiceUnavailableError",
    "InvalidStateTransitionError",
    "ResourceConflictError",
    "ResourceNotFoundError",
]
