"""API contract smoke tests."""

import asyncio

import httpx

from app.main import app


async def request(method: str, path: str, json: dict | None = None) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, json=json)


def test_health() -> None:
    response = asyncio.run(request("GET", "/health"))

    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_chat_routes_to_network_agent() -> None:
    response = asyncio.run(
        request("POST", "/api/chat/", {"message": "ping router R1"})
    )

    assert response.status_code == 200
    assert response.json()["agent"] == "network_agent"


def test_chat_rejects_blank_message() -> None:
    response = asyncio.run(request("POST", "/api/chat/", {"message": "  "}))

    assert response.status_code == 422


def test_agents_endpoint() -> None:
    response = asyncio.run(request("GET", "/api/agents/"))

    assert response.status_code == 200
    assert response.json() == {"agents": ["network_agent", "analyst_agent"]}
