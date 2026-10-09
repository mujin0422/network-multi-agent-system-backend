"""Agent application-layer unit tests."""

import asyncio

import pytest

from app.agents.analyst import AnalystAgent
from app.agents.manager import AgentManager
from app.agents.network import NetworkAgent
from app.agents.registry import AgentNotFoundError, AgentRegistry


def test_manager_routes_messages() -> None:
    manager = AgentManager(AgentRegistry([NetworkAgent(), AnalystAgent()]))

    network_result = asyncio.run(manager.process("Check the SWITCH"))
    analyst_result = asyncio.run(manager.process("Summarize this"))

    assert network_result.agent == "network_agent"
    assert analyst_result.agent == "analyst_agent"


def test_registry_raises_lookup_error_for_unknown_agent() -> None:
    registry = AgentRegistry()

    with pytest.raises(AgentNotFoundError, match="missing"):
        registry.get("missing")
