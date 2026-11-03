"""Capture a safe, append-only audit trail for versioned business mutations.

No request/response bodies, credentials, authorization headers, or commands
are persisted. The route allowlist makes audited actions explicit. The
business operation finishes before this independent audit insert; a logging
failure is surfaced to server logs, never misrepresented to the API caller as
a failed business operation after it already committed.
"""

import logging
from uuid import UUID

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.domains.audit.routers.dependencies import get_audit_log_service
from app.domains.audit.schemas import (
    AuditActorType,
    AuditEventStatus,
    AuditLogCreate,
)
from app.domains.identity.routers.dependencies import get_identity_service

logger = logging.getLogger(__name__)

# method, FastAPI's matched route template -> action, resource, ID field
AUDITED_ROUTES: dict[tuple[str, str], tuple[str, str, str | None]] = {
    ("POST", "/api/v1/auth/login"): ("AUTH_LOGIN", "USER", None),
    ("POST", "/api/v1/auth/refresh"): ("AUTH_REFRESH", "USER", None),
    ("POST", "/api/v1/auth/logout"): ("AUTH_LOGOUT", "USER", None),
    ("POST", "/api/v1/users/"): ("USER_CREATE", "USER", None),
    ("PATCH", "/api/v1/users/{user_id}"): ("USER_UPDATE", "USER", "user_id"),
    ("POST", "/api/v1/roles/"): ("ROLE_CREATE", "ROLE", None),
    ("PATCH", "/api/v1/roles/{role_id}"): ("ROLE_UPDATE", "ROLE", "role_id"),
    ("PUT", "/api/v1/roles/{role_id}/permissions"): (
        "ROLE_PERMISSIONS_REPLACE", "ROLE", "role_id"
    ),
    ("POST", "/api/v1/brands/"): ("BRAND_CREATE", "BRAND", None),
    ("PATCH", "/api/v1/brands/{brand_id}"): ("BRAND_UPDATE", "BRAND", "brand_id"),
    ("POST", "/api/v1/devices/"): ("DEVICE_CREATE", "DEVICE", None),
    ("PATCH", "/api/v1/devices/{device_id}"): (
        "DEVICE_UPDATE", "DEVICE", "device_id"
    ),
    ("POST", "/api/v1/credentials/"): ("CREDENTIAL_CREATE", "CREDENTIAL", None),
    ("PATCH", "/api/v1/credentials/{credential_id}"): (
        "CREDENTIAL_UPDATE", "CREDENTIAL", "credential_id"
    ),
    ("POST", "/api/v1/conversations/messages"): (
        "CONVERSATION_CREATE", "CONVERSATION", None
    ),
    ("PATCH", "/api/v1/conversations/{conversation_id}/title"): (
        "CONVERSATION_RENAME", "CONVERSATION", "conversation_id"
    ),
    ("POST", "/api/v1/conversations/{conversation_id}/messages"): (
        "MESSAGE_CREATE", "CONVERSATION", "conversation_id"
    ),
    ("POST", "/api/v1/tasks/"): ("TASK_CREATE", "TASK", None),
    ("POST", "/api/v1/tasks/{task_id}/operations"): (
        "OPERATION_CREATE", "OPERATION", None
    ),
    ("POST", "/api/v1/operation-device-approvals/{approval_id}/decision"): (
        "APPROVAL_DECISION", "APPROVAL", "approval_id"
    ),
    ("POST", "/api/v1/benchmarks/scenarios"): (
        "BENCHMARK_SCENARIO_CREATE", "BENCHMARK_SCENARIO", None
    ),
    ("PATCH", "/api/v1/benchmarks/scenarios/{scenario_id}"): (
        "BENCHMARK_SCENARIO_UPDATE", "BENCHMARK_SCENARIO", "scenario_id"
    ),
    ("POST", "/api/v1/benchmarks/runs"): (
        "BENCHMARK_RUN_START", "BENCHMARK_RUN", None
    ),
    ("POST", "/api/v1/benchmarks/runs/{run_id}/cleanup"): (
        "BENCHMARK_RUN_CLEANUP", "BENCHMARK_RUN", "run_id"
    ),
}


def _request_uuid(raw: str | None) -> UUID | None:
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError:
        return None


async def _optional_actor(request: Request):
    """Identity middleware dependency is authoritative; verify optional token
    for inventory routes that predate authentication dependencies.
    """
    actor = getattr(request.state, "audit_actor", None)
    if actor is not None:
        return actor
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        return None
    try:
        override = request.app.dependency_overrides.get(get_identity_service)
        service = await (override or get_identity_service)()
        actor, _session_id = await run_in_threadpool(
            service.authenticate, authorization.removeprefix("Bearer ").strip()
        )
        return actor
    except Exception:
        # An invalid or revoked token must never be trusted as an audit identity.
        # Only the authentication failure outcome is captured; never its secret.
        return None


class AuditCaptureMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        try:
            response = await call_next(request)
        except Exception:
            await self._record(request, 500)
            raise
        await self._record(request, response.status_code)
        return response

    async def _record(self, request: Request, status_code: int) -> None:
        route = request.scope.get("route")
        if route is None:
            return
        matched_path = getattr(route, "path", None)
        rule = AUDITED_ROUTES.get((request.method, matched_path))
        if rule is None:
            return
        action, resource_type, path_field = rule
        if status_code in (401, 403):
            outcome = AuditEventStatus.DENIED
        elif 200 <= status_code < 300:
            outcome = AuditEventStatus.SUCCESS
        else:
            outcome = AuditEventStatus.FAILED

        actor = await _optional_actor(request)
        resource_id = (
            getattr(request.state, "audit_resource_id", None)
            or (request.path_params.get(path_field) if path_field else None)
        )
        if resource_id is not None:
            resource_id = str(resource_id)[:64]
        if getattr(request.state, "audit_action", None):
            action = request.state.audit_action
        payload = AuditLogCreate(
            actor_type=AuditActorType.USER if actor else AuditActorType.SYSTEM,
            actor_user_id=actor.id if actor else None,
            actor_display_name=actor.full_name if actor else "Unauthenticated request",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            event_status=outcome,
            summary=f"{action.replace('_', ' ').title()} (HTTP {status_code})",
            event_data={
                "method": request.method,
                "route": matched_path,
                "http_status": status_code,
            },
            request_id=_request_uuid(request.headers.get("x-request-id")),
            source_ip=request.client.host if request.client else None,
            # Deliberately omit arbitrary User-Agent and body content.
        )
        try:
            audit_service = getattr(request.app.state, "audit_service", None)
            if audit_service is None:
                audit_service = await get_audit_log_service()
            await run_in_threadpool(audit_service.record, payload)
        except Exception:
            # Do not report the already-committed mutation as a failed request.
            # Operators must alert on this error; see Audit domain README.
            logger.exception(
                "SYSTEM AUDIT WRITE FAILED: action=%s resource_type=%s status=%s",
                action, resource_type, status_code,
            )
