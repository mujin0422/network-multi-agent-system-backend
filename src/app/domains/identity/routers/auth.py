"""Authentication and current-user endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.concurrency import run_in_threadpool

from app.domains.identity.routers.dependencies import get_current_identity, get_identity_service
from app.domains.identity.schemas import LoginRequest, RefreshRequest, TokenResponse, User
from app.domains.identity.services import IdentityService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    request: Request,
) -> TokenResponse:
    result = await run_in_threadpool(service.login, payload.email.strip().lower(), payload.password)
    user, _ = await run_in_threadpool(service.authenticate, result.access_token)
    request.state.audit_actor = user
    request.state.audit_resource_id = user.id
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    service: Annotated[IdentityService, Depends(get_identity_service)],
    request: Request,
) -> TokenResponse:
    result = await run_in_threadpool(service.refresh, payload.refresh_token)
    user, _ = await run_in_threadpool(service.authenticate, result.access_token)
    request.state.audit_actor = user
    request.state.audit_resource_id = user.id
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    identity: Annotated[tuple[User, str], Depends(get_current_identity)],
    service: Annotated[IdentityService, Depends(get_identity_service)],
    request: Request,
) -> Response:
    request.state.audit_resource_id = identity[0].id
    service.logout(UUID(identity[1]))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=User)
async def me(identity: Annotated[tuple[User, str], Depends(get_current_identity)]) -> User:
    return identity[0]
