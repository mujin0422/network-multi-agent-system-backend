"""FastAPI dependency composition for identity use cases."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.domains.identity.repositories import PostgresIdentityRepository
from app.domains.identity.services import IdentityService
from app.domains.identity.schemas import User

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _build_identity_service() -> IdentityService:
    settings = get_settings()
    return IdentityService(PostgresIdentityRepository(settings.database_url), settings)


async def get_identity_service() -> IdentityService:
    return _build_identity_service()


async def get_current_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
) -> tuple[User, str]:
    from app.core.exceptions import AuthenticationError
    if credentials is None:
        raise AuthenticationError("Cần đăng nhập để thực hiện thao tác này")
    user, session_id = service.authenticate(credentials.credentials)
    return user, str(session_id)


def require_permission(function: str, action: str):
    async def dependency(
        identity: Annotated[tuple[User, str], Depends(get_current_identity)],
        service: Annotated[IdentityService, Depends(get_identity_service)],
    ) -> User:
        user, _ = identity
        service.require_permission(user, function, action)
        return user
    return dependency
