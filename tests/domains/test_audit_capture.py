"""End-to-end HTTP audit capture tests, without a live PostgreSQL server."""

import asyncio
import json
from types import SimpleNamespace

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.routing import APIRoute

from app.domains.audit.http_capture import AUDITED_ROUTES, AuditCaptureMiddleware
from app.domains.audit.schemas import AuditActorType, AuditEventStatus
from app.main import app as application
from app.domains.inventory.routers.dependencies import get_brand_service
from app.domains.inventory.schemas import Brand


class MemoryAuditService:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)


async def request(app, method, path, payload=None, headers=None):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        return await client.request(method, path, json=payload, headers=headers)


def build_test_app(service):
    app = FastAPI()
    app.state.audit_service = service
    app.add_middleware(AuditCaptureMiddleware)

    @app.post("/api/v1/devices/", status_code=201)
    async def create_device(request: Request, payload: dict):
        request.state.audit_actor = SimpleNamespace(
            id="user-test",
            full_name="Network Admin",
        )
        request.state.audit_resource_id = "devc-1"
        return {"id": "devc-1", "hostname": "P1"}

    @app.patch("/api/v1/devices/{device_id}")
    async def update_device(device_id: str):
        raise HTTPException(status_code=403, detail="Forbidden")

    @app.get("/api/v1/devices/")
    async def list_devices():
        return []

    @app.post("/api/v1/unmapped-action")
    async def other_action():
        return {"ok": True}

    return app


def test_create_audits_authenticated_actor_without_recording_secrets():
    service = MemoryAuditService()
    api = build_test_app(service)

    response = asyncio.run(request(api, "POST", "/api/v1/devices/", {
        "password": "NEVER_LOG_THIS",
        "authorization": "NEVER_LOG_THIS",
        "commands": ["secret command"],
    }))
    assert response.status_code == 201
    assert len(service.events) == 1
    event = service.events[0]
    assert event.actor_type == AuditActorType.USER
    assert event.actor_user_id == "user-test"
    assert event.actor_display_name == "Network Admin"
    assert event.action == "DEVICE_CREATE"
    assert event.resource_type == "DEVICE"
    assert event.resource_id == "devc-1"
    assert event.event_status == AuditEventStatus.SUCCESS
    assert event.event_data == {
        "method": "POST",
        "route": "/api/v1/devices/",
        "http_status": 201,
    }
    serialized = json.dumps(event.model_dump(mode="json"))
    assert "NEVER_LOG_THIS" not in serialized
    assert "secret command" not in serialized


def test_denied_write_creates_denied_event_without_read_log():
    service = MemoryAuditService()
    api = build_test_app(service)

    denied = asyncio.run(request(api, "PATCH", "/api/v1/devices/devc-7"))
    read = asyncio.run(request(api, "GET", "/api/v1/devices/"))
    unknown = asyncio.run(request(api, "POST", "/api/v1/unmapped-action"))

    assert denied.status_code == 403
    assert read.status_code == 200
    assert unknown.status_code == 200
    assert len(service.events) == 1
    assert service.events[0].event_status == AuditEventStatus.DENIED
    assert service.events[0].resource_id == "devc-7"
    assert service.events[0].action == "DEVICE_UPDATE"


def test_audit_storage_outage_does_not_misreport_committed_mutation(caplog):
    class UnavailableAuditService:
        def record(self, _event):
            raise ConnectionError("audit database unreachable")

    api = build_test_app(UnavailableAuditService())
    response = asyncio.run(request(api, "POST", "/api/v1/devices/", {"hostname": "P1"}))

    assert response.status_code == 201
    assert "SYSTEM AUDIT WRITE FAILED" in caplog.text


def test_every_registered_mutating_business_endpoint_has_an_audit_action():
    uncovered = [
        (method, route.path)
        for route in application.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/v1/")
        for method in route.methods
        if method in {"POST", "PATCH", "PUT", "DELETE"}
        and (method, route.path) not in AUDITED_ROUTES
    ]
    assert uncovered == []


def test_actual_app_wires_business_route_into_system_audit():
    """Covers main.py middleware registration and real Brand create endpoint."""
    service = MemoryAuditService()

    class StubBrandService:
        def create_brand(self, payload):
            return Brand(
                id="brnd-audit-test",
                name=payload.name,
                supported_drivers=payload.supported_drivers,
            )

    async def override_brand_service():
        return StubBrandService()

    application.dependency_overrides[get_brand_service] = override_brand_service
    application.state.audit_service = service
    try:
        response = asyncio.run(request(
            application,
            "POST",
            "/api/v1/brands/",
            {"name": "Audit-Test", "supported_drivers": ["cisco_ios"]},
        ))
        assert response.status_code == 201
        assert len(service.events) == 1
        event = service.events[0]
        assert event.action == "BRAND_CREATE"
        assert event.resource_id == "brnd-audit-test"
        assert event.event_status == AuditEventStatus.SUCCESS
        assert event.actor_type == AuditActorType.SYSTEM
    finally:
        application.dependency_overrides.pop(get_brand_service, None)
        del application.state.audit_service
