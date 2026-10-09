"""API integration tests cho ba domain thử nghiệm."""

import asyncio
from uuid import uuid4

import httpx

from app.main import app


async def request(method: str, path: str, json: dict | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, json=json)


def test_conversation_api_keeps_messages_in_the_parent_conversation() -> None:
    async def scenario() -> None:
        created = await request(
            "POST",
            "/api/conversations/",
            {"user_id": "user-test", "title": "Kiểm tra OSPF"},
        )
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        message = await request(
            "POST",
            f"/api/conversations/{conversation_id}/messages",
            {"sender_by": "USER", "message": "Kiểm tra neighbor trên P1"},
        )
        assert message.status_code == 201

        detail = await request("GET", f"/api/conversations/{conversation_id}")
        assert detail.status_code == 200
        assert detail.json()["messages"][0]["message"] == "Kiểm tra neighbor trên P1"

    asyncio.run(scenario())


def test_inventory_api_enforces_hostname_uniqueness() -> None:
    async def scenario() -> None:
        suffix = uuid4().hex[:8]
        payload = {
            "brand_id": "brnd-cisco",
            "category_id": "catg-router",
            "hostname": f"R-{suffix}",
            "host": "192.0.2.10",
            "port": int(suffix[:4], 16) % 50000 + 1024,
            "device_type": "cisco_ios",
            "last_updated_by": "user-test",
        }
        created = await request("POST", "/api/devices/", payload)
        duplicate = await request(
            "POST",
            "/api/devices/",
            {**payload, "host": "192.0.2.11", "port": payload["port"] + 1},
        )

        assert created.status_code == 201
        assert duplicate.status_code == 409
        assert "Hostname" in duplicate.json()["detail"]

    asyncio.run(scenario())


def test_execution_api_builds_and_approves_a_rollback_ready_change_set() -> None:
    async def scenario() -> None:
        source_message_id = f"mesg-test-{uuid4().hex}"
        task_response = await request(
            "POST",
            "/api/tasks/",
            {
                "conversation_id": "cons-test",
                "source_message_id": source_message_id,
                "user_id": "user-test",
                "input_message": "Cấu hình OSPF trên P3",
            },
        )
        assert task_response.status_code == 201
        task_id = task_response.json()["id"]

        operation_response = await request(
            "POST",
            f"/api/tasks/{task_id}/operations",
            {
                "intent": "CONFIGURE_OSPF",
                "display_order": 1,
                "parameters": {"process_id": 1},
            },
        )
        assert operation_response.status_code == 201
        operation_id = operation_response.json()["id"]

        change_response = await request(
            "POST",
            f"/api/operations/{operation_id}/change-sets",
            {
                "device_id": "devc-p3",
                "pre_change_snapshot": "router ospf 10",
                "planned_commands": ["router ospf 1"],
                "rollback_commands": ["no router ospf 1"],
                "verification_checks": ["show ip ospf neighbor"],
            },
        )
        assert change_response.status_code == 201
        assert change_response.json()["status"] == "WAITING_APPROVAL"

        change_set_id = change_response.json()["id"]
        approved = await request(
            "POST",
            f"/api/change-sets/{change_set_id}/approve",
            {"approved_by": "user-test"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "APPROVED"
        assert approved.json()["rollback_commands"] == ["no router ospf 1"]

    asyncio.run(scenario())
