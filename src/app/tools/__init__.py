"""Framework adapters through which agents call domain services."""

from app.tools.network import (
    CommandResult,
    NetmikoNetworkTool,
    NetworkTool,
    NornirNetworkTool,
)

__all__ = [
    "CommandResult",
    "NetmikoNetworkTool",
    "NetworkTool",
    "NornirNetworkTool",
]
