"""Contracts thuộc Conversation domain."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MessageSender(StrEnum):
    USER = "USER"
    AGENT = "AGENT"


class ConversationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=255)


class MessageCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    sender_by: MessageSender
    message: str = Field(min_length=1)


class Message(BaseModel):
    id: str
    conversation_id: str
    sender_by: MessageSender
    message: str
    created_at: datetime


class Conversation(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    last_updated_at: datetime


class ConversationDetail(Conversation):
    messages: list[Message] = Field(default_factory=list)
