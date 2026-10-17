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
            "/api/v1/conversations/",
            {"user_id": "user-test", "title": "Kiểm tra OSPF"},
        )
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        message = await request(
            "POST",
            f"/api/v1/conversations/{conversation_id}/messages",
            {"sender_by": "USER", "message": "Kiểm tra neighbor trên P1"},
        )
        assert message.status_code == 201

        detail = await request("GET", f"/api/v1/conversations/{conversation_id}")
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
        created = await request("POST", "/api/v1/devices/", payload)
        duplicate = await request(
            "POST",
            "/api/v1/devices/",
            {**payload, "host": "192.0.2.11", "port": payload["port"] + 1},
        )

        assert created.status_code == 201
        assert duplicate.status_code == 409
        assert "Hostname" in duplicate.json()["detail"]

    asyncio.run(scenario())


def test_execution_api_creates_task_and_operation() -> None:
    async def scenario() -> None:
        source_message_id = f"mesg-test-{uuid4().hex}"
        task_response = await request(
            "POST",
            "/api/v1/tasks/",
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
            f"/api/v1/tasks/{task_id}/operations",
            {
                "operation_intent": "CONFIGURE_OSPF",
                "display_order": 1,
                "operation_parameters": {"process_id": 1},
            },
        )
        assert operation_response.status_code == 201
        assert operation_response.json()["task_id"] == task_id
        assert operation_response.json()["operation_intent"] == "CONFIGURE_OSPF"

        detail_response = await request("GET", f"/api/v1/tasks/{task_id}")
        assert detail_response.status_code == 200
        assert len(detail_response.json()["operations"]) == 1

    asyncio.run(scenario())
