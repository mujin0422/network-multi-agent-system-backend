"""Network readiness contract exposed by the Inventory domain."""

from pydantic import BaseModel


class NetworkStatus(BaseModel):
    status: str
