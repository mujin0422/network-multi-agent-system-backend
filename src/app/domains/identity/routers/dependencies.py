"""FastAPI dependency composition for identity use cases."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.domains.identity.repositories import IdentityRepository
from app.domains.identity.schemas import User
from app.domains.identity.services import (
    AccessControlService,
    IdentityService,
    RoleService,
    UserService,
)

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def _build_identity_repository() -> IdentityRepository:
    return IdentityRepository(get_settings().database_url)


@lru_cache
def _build_identity_service() -> IdentityService:
    return IdentityService(_build_identity_repository(), get_settings())


@lru_cache
def _build_user_service() -> UserService:
    return UserService(_build_identity_repository())


@lru_cache
def _build_role_service() -> RoleService:
    return RoleService(_build_identity_repository())


@lru_cache
def _build_access_control_service() -> AccessControlService:
    return AccessControlService(_build_identity_repository())


async def get_identity_service() -> IdentityService:
    return _build_identity_service()


async def get_user_service() -> UserService:
    return _build_user_service()


async def get_role_service() -> RoleService:
    return _build_role_service()


async def get_access_control_service() -> AccessControlService:
    return _build_access_control_service()


async def get_current_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
    request: Request,
) -> tuple[User, str]:
    if credentials is None:
        raise AuthenticationError("Cần đăng nhập để thực hiện thao tác này")
    user, session_id = service.authenticate(credentials.credentials)
    request.state.audit_actor = user
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
