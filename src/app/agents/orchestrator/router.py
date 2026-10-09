"""Deterministic routing policy for the current agent set."""

NETWORK_KEYWORDS = frozenset({"router", "switch", "ping", "network"})


def route(message: str) -> str:
    """Select the network agent when a network keyword is present."""
    normalized_message = message.casefold()
    if any(keyword in normalized_message for keyword in NETWORK_KEYWORDS):
        return "network_agent"
    return "analyst_agent"
