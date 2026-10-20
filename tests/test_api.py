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


def test_agent_internal_apis_are_not_exposed() -> None:
    chat_response = asyncio.run(request("POST", "/api/v1/chat/", {"message": "ping"}))
    agents_response = asyncio.run(request("GET", "/api/v1/agents/"))

    assert chat_response.status_code == 404
    assert agents_response.status_code == 404


def test_unversioned_api_is_not_exposed() -> None:
    response = asyncio.run(request("GET", "/api/agents/"))

    assert response.status_code == 404
