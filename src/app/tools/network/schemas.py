"""Kết quả thô trả về từ network tool."""

from pydantic import BaseModel


class CommandResult(BaseModel):
    command: str
    output: str
