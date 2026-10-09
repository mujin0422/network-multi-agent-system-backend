"""HTTP routes của Conversation domain."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_conversation_service
from app.domains.conversation.schemas import (
    Conversation,
    ConversationCreate,
    ConversationDetail,
    Message,
    MessageCreate,
)
from app.domains.conversation.service import ConversationService


router = APIRouter()


@router.post("/", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Conversation:
    return service.create(payload)


@router.get("/", response_model=list[Conversation])
async def list_conversations(
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    user_id: Annotated[str | None, Query()] = None,
) -> list[Conversation]:
    return service.list(user_id)


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ConversationDetail:
    return service.get(conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
)
async def add_message(
    conversation_id: str,
    payload: MessageCreate,
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> Message:
    return service.add_message(conversation_id, payload)
