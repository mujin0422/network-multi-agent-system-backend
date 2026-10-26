"""Public persistence contracts của Identity domain."""

from app.domains.identity.repositories.identity import (
    IdentityRepository,
    IdentityRepositoryProtocol,
)
from app.domains.identity.repositories.role import (
    RoleRepository,
    RoleRepositoryProtocol,
)
from app.domains.identity.repositories.role_permission import (
    RolePermissionRepository,
    RolePermissionRepositoryProtocol,
)
from app.domains.identity.repositories.user import (
    UserRepository,
    UserRepositoryProtocol,
)
from app.domains.identity.repositories.user_session import (
    UserSessionRepository,
    UserSessionRepositoryProtocol,
)

__all__ = [
    "IdentityRepository",
    "IdentityRepositoryProtocol",
    "UserRepository",
    "UserRepositoryProtocol",
    "RoleRepository",
    "RoleRepositoryProtocol",
    "RolePermissionRepository",
    "RolePermissionRepositoryProtocol",
    "UserSessionRepository",
    "UserSessionRepositoryProtocol",
]
